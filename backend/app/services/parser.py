"""Statement file parsing (CSV / JSON) into a normalized transaction frame.

Parsing strategy:
- CSV is tokenized with the standard-library `csv` module (correct handling
  of quoted fields, escaped double quotes, commas/newlines inside values,
  and LF/CRLF/CR line endings). The delimiter is chosen by trying `,`, `;`,
  tab and `|` until one of them produces a usable header row, so `;`-separated
  exports (common outside the US) work too.
- The header row is FOUND, not assumed: bank exports often start with a
  preamble ("NORTH SHORE CREDIT UNION", "Account: 1234") and end with footer
  rows ("TOTAL DEBITS", "Closing Balance"). Those are skipped and reported,
  never imported as transactions.
- Rows whose field count does not match the header are REJECTED with an
  explicit, line-numbered warning; valid rows still import. Nothing is ever
  silently dropped.
- Columns are matched by NAME (case/whitespace/punctuation-insensitive)
  against alias tables, so order and extra columns do not matter.
- Date order (DD/MM vs MM/DD) is inferred from unambiguous rows in the file
  and the choice is reported as a warning instead of being hidden. A file that
  contradicts itself is reported as mixed rather than silently resolved.
- Sign convention: expenses/withdrawals/debits are negative, income/
  deposits/credits are positive. When both an Amount column and
  Debit/Credit columns exist, Amount takes documented precedence.
"""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from datetime import date
from typing import List, Optional, Tuple

import pandas as pd

_CURRENCY_NOISE = re.compile(r"[\$€£,\s]")
_SEPARATORS = re.compile(r"[\s_\-/().]+")
_THOUSANDS_DOT = re.compile(r"\.(?=\d{3}(\D|$))")
_SLASH_DATE = re.compile(r"^\s*(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\s*$")
# YYYY-MM-DD, optionally with a time and zone suffix. Deliberately narrow: any
# other spelling falls through to the general parser below.
_ISO_DATE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?"
    r"(?:[+-]\d{2}:?\d{2})?)?$"
)

DATE_ALIASES = [
    "date", "transaction date", "posted date", "posting date", "value date",
    "paid on", "date paid", "transaction time", "booking date",
    "datum", "fecha", "date de lopration", "data transazionale",
]
# Aliases that only count as a full-header match, because they are also
# English words that can appear inside an unrelated column name
# ("Card data", "Freight cargo").
DATE_ALIASES_EXACT = ["data"]
DEBIT_ALIASES_EXACT = ["cargo"]
DESCRIPTION_ALIASES = [
    "description", "payee", "merchant", "merchant name", "memo", "narrative",
    "details", "transaction description", "card description",
    "beschreibung", "omschrijving", "description de lopration", "libelle",
    "descrizione", "descripcion", "purpose",
]
AMOUNT_ALIASES = [
    "amount", "transaction amount", "value", "betrag", "bedrag", "importo",
    "importe", "montant",
]
DEBIT_ALIASES = [
    "debit", "debits", "withdrawal", "withdrawals", "money out", "paid out",
    "outflow", "soll", "addebito", "uitgave",
]
CREDIT_ALIASES = [
    "credit", "credits", "deposit", "deposits", "money in", "paid in",
    "inflow", "haben", "accredito", "ontvangst", "abono",
]
CATEGORY_ALIASES = ["category", "tax category", "assigned category", "categorie", "categoria"]
STATUS_ALIASES = ["status", "review status"]

# Non-English column names, used only as a style hint for date order. A file
# exported with these headings (or with `;`/`|` delimiters, which already imply
# decimal-comma amounts) writes dates day-first far more often than US-first.
_CONTINENTAL_ALIASES = frozenset({
    "datum", "fecha", "beschreibung", "omschrijving", "libelle", "descrizione",
    "descripcion", "betrag", "bedrag", "importo", "importe", "montant",
    "soll", "haben", "addebito", "accredito", "uitgave", "ontvangst", "abono",
})

DELIMITERS = [",", ";", "\t", "|"]

# Anchored so that a real merchant called "TOTAL FOOD MARKET" is never
# mistaken for a statement footer.
FOOTER_CELL = re.compile(
    r"^(?:"
    r"total(?:s)?(?:[ _-]?(?:debits?|credits?|purchases?|charges?|deposits?"
    r"|withdrawals?|amount|due|paid|spent|income|expenses?|tax|federal|provincial))?"
    r"|subtotals?(?:[ _-]?(?:debits?|credits?|amount|due|tax))?"
    r"|net(?:[ _-]?(?:amount|total|change|balance|due|paid))?"
    r"|(?:opening|closing|new|previous|current)[ _-]balance"
    r"|balance[ _-](?:carried|brought)[ _-]forward"
    r"|amount(?:[ _-]?(?:owed|overpaid|over))?"
    r"|page[ _-]\d+(?:[ _-]of[ _-]\d+)?"
    r"|interest[ _-]charged(?:[ _-]total)?"
    r")$",
    re.IGNORECASE,
)


class ParseError(ValueError):
    """Raised when an uploaded file cannot be interpreted as a statement."""

    def __init__(self, message: str, row: Optional[int] = None) -> None:
        super().__init__(message)
        self.row = row


def _canonical(name: str) -> str:
    """Normalize a header cell for alias matching.

    Lowercases, folds accents, and collapses separators so that
    "Transaction_Date", "TRANSACTION DATE" and "date de l'opération" all
    resolve the same way.
    """
    text = unicodedata.normalize("NFKD", str(name).lower().strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("'", "")
    return _SEPARATORS.sub(" ", text).strip()


def _looks_like_footer(values: List[str]) -> bool:
    """True for statement furniture (totals, balances, page numbers)."""
    return any(FOOTER_CELL.match(str(cell).strip()) for cell in values if str(cell).strip())


def _find_column(
    canonical_headers: List[str],
    aliases: List[str],
    exclude: set = frozenset(),
    exact_aliases: List[str] = (),
) -> Optional[int]:
    """Return the index of the first column matching an alias.

    Exact alias matches (including `exact_aliases`, which never substring
    match) win over substring matches, and earlier aliases win over later
    ones, keeping resolution deterministic. Already-assigned column indices
    are excluded so e.g. a "Value Date" column can never be mistaken for a
    "value" (amount) column.
    """
    for alias in [*aliases, *exact_aliases]:
        for index, header in enumerate(canonical_headers):
            if index not in exclude and header == alias:
                return index
    for alias in aliases:
        for index, header in enumerate(canonical_headers):
            if index not in exclude and alias in header:
                return index
    return None


def _to_amount(
    value, *, field: str = "Amount", row: Optional[int] = None, decimal_comma: bool = False
) -> Optional[float]:
    """Coerce a currency-ish cell to a signed float. Empty returns None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    text = str(value).strip()
    if not text:
        return None
    if decimal_comma:  # "1.234,56" / "1234,56" from ;-separated exports
        text = _THOUSANDS_DOT.sub("", text).replace(",", ".")
    negative = text.startswith("(") and text.endswith(")")
    cleaned = _CURRENCY_NOISE.sub("", text.replace("(", "").replace(")", ""))
    cleaned = cleaned.replace("+", "")
    if cleaned.endswith("-"):  # trailing-minus convention: "12.34-"
        cleaned, negative = cleaned[:-1], True
    try:
        amount = float(cleaned)
    except ValueError:
        location = f" on row {row}" if row else ""
        raise ParseError(
            f"{field} value '{value}'{location} is not a recognizable amount. "
            "Use plain numbers like -84.21 or $84.21.",
            row=row,
        )
    if pd.isna(amount):
        return None
    return -amount if negative else amount


def _detect_dayfirst(
    raw_dates: List[str], european: bool = False
) -> Tuple[Optional[bool], Optional[str]]:
    """Infer date order from unambiguous samples. None means no evidence.

    `european` is a hint from the file's own number/header style: a file whose
    amounts already use a decimal comma should not have its ambiguous dates read
    the US way, because that pairing mis-dates rows into the wrong month.
    """
    day_first = month_first = ambiguous = False
    day_example = month_example = ""
    for text in raw_dates:
        match = _SLASH_DATE.match(str(text))
        if not match:
            continue
        first, second = int(match.group(1)), int(match.group(2))
        if first > 12:
            day_first, day_example = True, str(text)
        elif second > 12:
            month_first, month_example = True, str(text)
        else:
            ambiguous = True
    if day_first and month_first:
        # Contradictory file: no single reading can be right for every row, so
        # the conflict is reported instead of being resolved silently.
        return False, (
            f"This file mixes date orders: '{day_example}' is day-first but "
            f"'{month_example}' is month-first. Dates were read as MM/DD/YYYY; "
            "check the affected rows before exporting."
        )
    if day_first:
        return True, (
            f"Dates were read as DD/MM/YYYY — '{day_example}' can only be "
            "day-first. Tell us if that is wrong."
        )
    if month_first:
        return False, (
            f"Dates were read as MM/DD/YYYY — '{month_example}' can only be "
            "month-first."
        )
    if ambiguous:
        if european:
            return True, (
                "Some dates are ambiguous between DD/MM/YYYY and MM/DD/YYYY; "
                "read as DD/MM/YYYY because this file writes amounts and "
                "headings the continental way. Tell us if that is wrong."
            )
        return False, (
            "Some dates are ambiguous between DD/MM/YYYY and MM/DD/YYYY; "
            "assumed MM/DD/YYYY (US order)."
        )
    return None, None


def _to_date(value, row: Optional[int] = None, dayfirst: bool = False) -> str:
    text = str(value).strip() if value is not None else ""
    if not text or text.lower() in ("nan", "none"):
        location = f" on row {row}" if row else ""
        raise ParseError(f"Missing or empty date{location}.", row=row)

    # ISO is unambiguous and by far the most common spelling in bank exports,
    # so it never reaches pandas: per-value to_datetime() re-guesses the format
    # every call and that alone was ~90% of parse time (a 10 MB-limit file
    # blew past the proxy timeout without this shortcut).
    iso = _ISO_DATE.match(text)
    if iso:
        try:
            return date.fromisoformat(iso.group(1)).isoformat()
        except ValueError:
            location = f" on row {row}" if row else ""
            raise ParseError(
                f"Date '{value}'{location} could not be understood. "
                "Try the format YYYY-MM-DD.",
                row=row,
            )

    # Numeric d/m/y is where banks put DD/MM vs MM/DD ambiguity, so it is
    # resolved here from the file's own evidence instead of letting pandas
    # guess (a guess it makes with a warning, per value).
    numeric = _SLASH_DATE.match(text)
    if numeric:
        first, second, year = (
            int(numeric.group(1)), int(numeric.group(2)), int(numeric.group(3)),
        )
        if year < 100:
            year += 2000
        preferred = ((second, first), (first, second)) if dayfirst \
            else ((first, second), (second, first))
        for month, day in preferred:
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                continue

    parsed = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
    if pd.isna(parsed):
        location = f" on row {row}" if row else ""
        raise ParseError(
            f"Date '{value}'{location} could not be understood. "
            "Try the format YYYY-MM-DD.",
            row=row,
        )
    return parsed.strftime("%Y-%m-%d")


def parse_statement(content: bytes, filename: str) -> Tuple[pd.DataFrame, List[str]]:
    """Parse CSV or JSON bytes into (frame, warnings).

    Frame columns: original_index, date, description, amount,
    imported_category (str, may be empty).
    """
    name = (filename or "").lower()
    text = content.decode("utf-8-sig", errors="replace")
    if not text.strip():
        raise ParseError("The uploaded file is empty.")

    if name.endswith(".json") or text.lstrip()[:1] in ("[", "{"):
        records, warnings = _parse_json(text)
    else:
        records, warnings = _parse_csv(text)

    if not records:
        raise ParseError("No valid transactions were found in the file.")
    return pd.DataFrame(records), warnings


def _resolve_columns(headers: List[str]) -> dict:
    canonical = [_canonical(h) for h in headers]
    used: set = set()
    date_index = _find_column(canonical, DATE_ALIASES, exact_aliases=DATE_ALIASES_EXACT)
    if date_index is not None:
        used.add(date_index)
    desc_index = _find_column(canonical, DESCRIPTION_ALIASES, exclude=used)
    if desc_index is not None:
        used.add(desc_index)
    columns = {
        "date": date_index,
        "description": desc_index,
        "amount": _find_column(canonical, AMOUNT_ALIASES, exclude=used),
        "debit": None,
        "credit": None,
        "category": None,
        "status": None,
    }
    used.update({i for i in (columns["amount"],) if i is not None})
    columns["debit"] = _find_column(
        canonical, DEBIT_ALIASES, exclude=used, exact_aliases=DEBIT_ALIASES_EXACT
    )
    if columns["debit"] is not None:
        used.add(columns["debit"])
    columns["credit"] = _find_column(canonical, CREDIT_ALIASES, exclude=used)
    if columns["credit"] is not None:
        used.add(columns["credit"])
    columns["category"] = _find_column(canonical, CATEGORY_ALIASES, exclude=used)
    if columns["category"] is not None:
        used.add(columns["category"])
    columns["status"] = _find_column(canonical, STATUS_ALIASES, exclude=used)
    return columns


def _is_usable_header(headers: List[str]) -> bool:
    """A header row must identify date, description and an amount column."""
    columns = _resolve_columns(headers)
    return (
        columns["date"] is not None
        and columns["description"] is not None
        and (columns["amount"] is not None or columns["debit"] is not None
             or columns["credit"] is not None)
    )


def _require_columns(columns: dict, headers: List[str]) -> None:
    if columns["date"] is None:
        raise ParseError(
            "No date column found. Expected a column named like "
            "'Date' or 'Transaction Date'. Found: " + ", ".join(headers) + "."
        )
    if columns["description"] is None:
        raise ParseError(
            "No description column found. Expected a column named like "
            "'Description', 'Payee', or 'Merchant'. Found: "
            + ", ".join(headers) + "."
        )
    if columns["amount"] is None and columns["debit"] is None and columns["credit"] is None:
        raise ParseError(
            "No amount columns found. Expected 'Amount', or separate "
            "'Debit'/'Credit' (or 'Withdrawal'/'Deposit') columns. Found: "
            + ", ".join(headers) + "."
        )


def _tokenize(text: str, delimiter: str) -> List[Tuple[int, List[str]]]:
    """csv-tokenize the file, dropping genuinely blank lines."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows: List[Tuple[int, List[str]]] = []
    for line_number, values in enumerate(reader, start=1):
        if not any(str(cell).strip() for cell in values):
            continue
        rows.append((line_number, [str(v) for v in values]))
    return rows


def _find_header(rows: List[Tuple[int, List[str]]]) -> Optional[int]:
    """Index of the first row that identifies date, description and amount."""
    for position, (_line_number, values) in enumerate(rows[:25]):
        if _is_usable_header(values):
            return position
    return None


def _parse_csv(text: str) -> Tuple[List[dict], List[str]]:
    # A preamble line ("NORTH SHORE CREDIT UNION") carries no delimiter
    # evidence, so each candidate is tried until one produces a header row.
    chosen: Optional[Tuple[str, List[Tuple[int, List[str]]], int]] = None
    for delimiter in DELIMITERS:
        rows = _tokenize(text, delimiter)
        header_index = _find_header(rows)
        if header_index is not None:
            chosen = (delimiter, rows, header_index)
            break
    if chosen is None:
        rows = _tokenize(text, ",")
        if not rows:
            raise ParseError("The CSV file has no readable rows.")
        chosen = (",", rows, 0)
    delimiter, rows, header_index = chosen

    warnings: List[str] = []
    if header_index > 0:
        skipped = [" / ".join(v for v in values if v.strip())[:60]
                   for _, values in rows[:header_index]]
        warnings.append(
            f"Skipped {header_index} line(s) above the table header "
            f"({' / '.join(skipped[:3])})."
        )

    header_line, headers = rows[header_index]
    columns = _resolve_columns(headers)
    _require_columns(columns, headers)
    expected_fields = len(headers)
    canonical_header = [_canonical(h) for h in headers]
    decimal_comma = delimiter in (";", "|")

    # Second pass over the whole file for date-order evidence.
    raw_dates = [
        values[columns["date"]]
        for _line_number, values in rows[header_index + 1 :]
        if columns["date"] < len(values)
    ]
    dayfirst, date_note = _detect_dayfirst(
        raw_dates, european=decimal_comma
        or any(h in _CONTINENTAL_ALIASES for h in canonical_header)
    )
    if date_note:
        warnings.append(date_note)

    duplicate_headers = 0
    footer_rows = 0
    records: List[dict] = []
    for line_number, values in rows[header_index + 1 :]:
        if [_canonical(v) for v in values] == canonical_header:
            duplicate_headers += 1  # multi-page exports repeat the header
            continue
        if _looks_like_footer(values):
            footer_rows += 1
            continue
        if len(values) != expected_fields:
            warnings.append(
                f"Row {line_number} was skipped: it has {len(values)} fields "
                f"but the header has {expected_fields}. Check the quotation "
                "marks and commas in that row."
            )
            continue
        description = (values[columns["description"]] or "").strip()
        if description.lower() in ("nan", "none"):
            description = ""
        record = {
            "original_index": line_number,
            "date": _to_date(
                values[columns["date"]], row=line_number, dayfirst=bool(dayfirst)
            ),
            "description": description,
            "amount": _record_amount(values, columns, line_number, decimal_comma),
            "imported_category": (
                values[columns["category"]].strip()
                if columns["category"] is not None and columns["category"] < len(values)
                else ""
            ),
        }
        records.append(record)

    if duplicate_headers:
        warnings.append(
            f"Skipped {duplicate_headers} repeated header row(s) inside the file."
        )
    if footer_rows:
        warnings.append(
            f"Skipped {footer_rows} statement-total or balance row(s) — these "
            "are not transactions."
        )
    if not records:
        raise ParseError(
            "None of the CSV data rows could be parsed. " + (warnings[0] if warnings else "")
        )
    return records, warnings


def _record_amount(row_values: List[str], columns: dict, line: int,
                   decimal_comma: bool = False) -> float:
    """Apply the documented precedence: Amount column wins over Debit/Credit."""
    if columns["amount"] is not None:
        value = _to_amount(
            row_values[columns["amount"]], field="Amount", row=line,
            decimal_comma=decimal_comma,
        )
        if value is None:
            raise ParseError(f"Row {line} has an empty Amount value.", row=line)
        return value
    debit = _to_amount(
        row_values[columns["debit"]] if columns["debit"] is not None else "",
        field="Debit", row=line, decimal_comma=decimal_comma,
    )
    credit = _to_amount(
        row_values[columns["credit"]] if columns["credit"] is not None else "",
        field="Credit", row=line, decimal_comma=decimal_comma,
    )
    if debit is None and credit is None:
        raise ParseError(
            f"Row {line} has no value in either the debit or credit column.",
            row=line,
        )
    return (credit or 0.0) - (debit or 0.0)


def _parse_json(text: str) -> Tuple[List[dict], List[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(
            f"The JSON file is not valid: {exc.msg} (at character {exc.pos})."
        )
    if isinstance(payload, dict):
        for key in ("transactions", "data", "items", "rows"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            raise ParseError(
                "The JSON object must contain a 'transactions' array of objects."
            )
    if not isinstance(payload, list):
        raise ParseError("The JSON must be an array of transaction objects.")
    if not payload:
        raise ParseError("The statement contains no transactions.")
    if not all(isinstance(item, dict) for item in payload):
        raise ParseError("Every JSON transaction must be an object.")

    headers = [str(h) for h in payload[0].keys()]
    columns = _resolve_columns(headers)
    _require_columns(columns, headers)

    def cell(item: dict, index: Optional[int]):
        if index is None:
            return ""
        return item.get(headers[index], "")

    dayfirst, date_note = _detect_dayfirst(
        [str(cell(item, columns["date"])) for item in payload],
        european=any(_canonical(h) in _CONTINENTAL_ALIASES for h in headers),
    )
    warnings: List[str] = [date_note] if date_note else []

    records: List[dict] = []
    for position, item in enumerate(payload, start=1):
        row_values = [item.get(header, "") for header in headers]
        amount = _record_amount(row_values, columns, position)
        description = str(cell(item, columns["description"]) or "").strip()
        if description.lower() in ("nan", "none"):
            description = ""
        records.append(
            {
                "original_index": position,
                "date": _to_date(
                    cell(item, columns["date"]), row=position, dayfirst=bool(dayfirst)
                ),
                "description": description,
                "amount": amount,
                "imported_category": (
                    str(cell(item, columns["category"]) or "").strip()
                    if columns["category"] is not None
                    else ""
                ),
            }
        )
    return records, warnings
