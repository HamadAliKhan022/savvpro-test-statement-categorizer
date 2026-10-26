"""Parser tests: every supported CSV/JSON shape, plus safe-recovery behavior.

All data is synthetic and fictional.
"""

import json

import pytest

from app.services.parser import ParseError, parse_statement


def _csv(text: str, filename: str = "s.csv"):
    return parse_statement(text.encode("utf-8"), filename)


class TestBasicShapes:
    def test_standard_three_columns(self):
        frame, warnings = _csv("Date,Description,Amount\n2026-01-05,ACME PAYMENT,100.00\n")
        assert len(frame) == 1
        assert frame.iloc[0]["amount"] == 100.0
        assert warnings == []

    def test_reordered_columns(self):
        frame, _ = _csv("Amount,Description,Date\n-25.00,STARBUCKS,2026-01-05\n")
        row = frame.iloc[0]
        assert (row["date"], row["description"], row["amount"]) == (
            "2026-01-05",
            "STARBUCKS",
            -25.0,
        )

    def test_extra_optional_columns_ignored(self):
        frame, _ = _csv(
            "Date,Description,Amount,Balance,Check Number\n"
            "2026-01-05,STARBUCKS,-5.00,995.00,\n"
        )
        assert frame.iloc[0]["amount"] == -5.0

    def test_blank_lines_skipped(self):
        frame, _ = _csv(
            "Date,Description,Amount\n\n2026-01-05,A,-1.00\n\n2026-01-06,B,-2.00\n"
        )
        assert len(frame) == 2


class TestQuotingAndSpecialCharacters:
    def test_comma_inside_quoted_description(self):
        frame, _ = _csv(
            'Date,Description,Amount\n2026-01-05,"AMAZON MARKETPLACE, ORDER 123",-42.00\n'
        )
        assert frame.iloc[0]["description"] == "AMAZON MARKETPLACE, ORDER 123"

    def test_escaped_double_quotes(self):
        frame, _ = _csv(
            'Date,Description,Amount\n2026-01-05,"He said ""hello"" store",-3.00\n'
        )
        assert frame.iloc[0]["description"] == 'He said "hello" store'

    def test_newline_inside_quoted_field(self):
        frame, _ = _csv(
            'Date,Description,Amount\n2026-01-05,"Line one\nLine two",-9.00\n'
        )
        assert frame.iloc[0]["description"] == "Line one\nLine two"


class TestEncodingsAndLineEndings:
    def test_utf8_bom(self):
        raw = "\ufeffDate,Description,Amount\n2026-01-05,STARBUCKS,-5.00\n"
        frame, _ = parse_statement(raw.encode("utf-8-sig"), "bom.csv")
        assert frame.iloc[0]["description"] == "STARBUCKS"

    def test_crlf(self):
        frame, _ = _csv("Date,Description,Amount\r\n2026-01-05,A,-1.00\r\n2026-01-06,B,-2.00\r\n")
        assert len(frame) == 2

    def test_cr_only(self):
        frame, _ = _csv("Date,Description,Amount\r2026-01-05,A,-1.00\r")
        assert len(frame) == 1

    def test_unicode_description(self):
        frame, _ = _csv("Date,Description,Amount\n2026-01-05,Café Müller ☕,-4.50\n")
        assert "Müller" in frame.iloc[0]["description"]


class TestColumnAliases:
    @pytest.mark.parametrize(
        "header",
        ["Date,Description,Amount", "Transaction Date,Description,Amount", "Date,Payee,Amount",
         "Date,Merchant,Amount", "Posted Date,Memo,Amount"],
    )
    def test_recognized_headers(self, header):
        body = header + "\n2026-01-05,ACME STORE,-7.00\n"
        frame, _ = _csv(body)
        assert frame.iloc[0]["amount"] == -7.0

    def test_debit_credit_columns(self):
        frame, _ = _csv(
            "Date,Description,Debit,Credit\n"
            "2026-01-05,STARBUCKS,12.50,\n"
            "2026-01-06,CLIENT PAYMENT,,900.00\n"
        )
        amounts = list(frame["amount"])
        assert amounts == [-12.50, 900.00]

    def test_withdrawal_deposit_columns(self):
        frame, _ = _csv(
            "Date,Description,Withdrawal,Deposit\n2026-01-05,ATM,100.00,\n"
        )
        assert frame.iloc[0]["amount"] == -100.0

    def test_money_out_money_in_columns(self):
        frame, _ = _csv("Date,Description,Money Out,Money In\n2026-01-05,SALON,40.00,\n")
        assert frame.iloc[0]["amount"] == -40.0

    def test_amount_column_takes_precedence_over_debit_credit(self):
        # Documented precedence: when Amount exists it wins; the transaction
        # is counted exactly once.
        frame, _ = _csv(
            "Date,Description,Amount,Debit,Credit\n2026-01-05,ACME,-50.00,999.00,999.00\n"
        )
        assert frame.iloc[0]["amount"] == -50.0

    def test_value_date_not_mistaken_for_amount(self):
        frame, _ = _csv("Value Date,Description,Amount\n2026-01-05,ACME,-5.00\n")
        assert frame.iloc[0]["date"] == "2026-01-05"
        assert frame.iloc[0]["amount"] == -5.0


class TestAmountFormats:
    def test_currency_symbols_and_thousands(self):
        frame, _ = _csv('Date,Description,Amount\n2026-01-05,BEST BUY,"-$1,299.00"\n')
        assert frame.iloc[0]["amount"] == -1299.0

    def test_parentheses_negative(self):
        frame, _ = _csv("Date,Description,Amount\n2026-01-05,ACME,(75.25)\n")
        assert frame.iloc[0]["amount"] == -75.25

    def test_trailing_minus(self):
        frame, _ = _csv("Date,Description,Amount\n2026-01-05,ACME,75.25-\n")
        assert frame.iloc[0]["amount"] == -75.25

    def test_decimal_amounts_preserved(self):
        frame, _ = _csv("Date,Description,Amount\n2026-01-05,ACME,0.10\n2026-01-06,ACM,0.20\n")
        assert list(frame["amount"]) == [0.10, 0.20]


class TestSafeRecoveryAndErrors:
    def test_inconsistent_row_rejected_with_line_number_others_imported(self):
        text = (
            "Date,Description,Amount\n"
            "2026-01-05,GOOD ROW,-1.00\n"
            '2026-01-06,"BAD "ROW", -2.00, EXTRA\n'
            "2026-01-07,ALSO GOOD,-3.00\n"
        )
        frame, warnings = _csv(text)
        assert len(frame) == 2
        assert len(warnings) == 1
        assert "Row 3" in warnings[0]

    def test_empty_file(self):
        with pytest.raises(ParseError):
            _csv("")

    def test_missing_amount_column(self):
        with pytest.raises(ParseError) as exc:
            _csv("Date,Description\n2026-01-05,ACME\n")
        assert "amount" in str(exc.value).lower()

    def test_missing_date_column(self):
        with pytest.raises(ParseError) as exc:
            _csv("Description,Amount\nACME,-5.00\n")
        assert "date" in str(exc.value).lower()

    def test_invalid_date_names_row(self):
        with pytest.raises(ParseError) as exc:
            _csv("Date,Description,Amount\nnot-a-date,ACME,-5.00\n")
        assert "row 2" in str(exc.value)

    def test_iso_dates_with_a_timestamp_keep_the_local_date(self):
        frame, _ = _csv(
            "Date,Description,Amount\n"
            "2026-01-05T18:42:07,ACME,-5.00\n"
            "2026-01-06 09:15:00+08:00,BETA,-7.00\n"
        )
        assert list(frame["date"]) == ["2026-01-05", "2026-01-06"]

    def test_impossible_iso_calendar_date_is_still_rejected(self):
        # The fast path for YYYY-MM-DD must not be more forgiving than the
        # general parser it replaced.
        with pytest.raises(ParseError) as exc:
            _csv("Date,Description,Amount\n2026-02-30,ACME,-5.00\n")
        assert "row 2" in str(exc.value)
        assert "could not be understood" in str(exc.value)

    def test_iso_dates_are_never_day_first_swapped(self):
        frame, warnings = _csv(
            "Date,Description,Amount\n"
            "25/12/2026,ACME,-5.00\n"      # forces the file to read day-first
            "2026-03-04,BETA,-7.00\n"      # ISO: unambiguous regardless
        )
        assert list(frame["date"]) == ["2026-12-25", "2026-03-04"]
        assert any("DD/MM/YYYY" in w for w in warnings)

    def test_invalid_amount_names_row(self):
        with pytest.raises(ParseError) as exc:
            _csv("Date,Description,Amount\n2026-01-05,ACME,banana\n")
        assert "banana" in str(exc.value)

    def test_empty_amount_value(self):
        with pytest.raises(ParseError) as exc:
            _csv("Date,Description,Amount\n2026-01-05,ACME,\n")
        assert "row 2" in str(exc.value).lower()


class TestJsonShapes:
    def test_top_level_array(self):
        payload = json.dumps([
            {"Date": "2026-01-05", "Description": "ACME", "Amount": -5.0},
        ])
        frame, _ = parse_statement(payload.encode(), "s.json")
        assert frame.iloc[0]["amount"] == -5.0

    def test_transactions_wrapper_with_debit_credit(self):
        payload = json.dumps({
            "transactions": [
                {"date": "2026-01-05", "description": "STARBUCKS", "debit": 6.0, "credit": None},
                {"date": "2026-01-06", "description": "INTEREST", "debit": None, "credit": 4.0},
            ]
        })
        frame, _ = parse_statement(payload.encode(), "s.json")
        assert list(frame["amount"]) == [-6.0, 4.0]

    def test_invalid_json_message(self):
        with pytest.raises(ParseError) as exc:
            parse_statement(b"{not json", "s.json")
        assert "JSON" in str(exc.value)

    def test_csv_content_routed_by_extension(self):
        frame, _ = parse_statement(
            b"Date,Description,Amount\n2026-01-05,ACME,-1.00", "statement.csv"
        )
        assert len(frame) == 1


class TestExportedFormatRoundTrip:
    """The application's own export format must re-upload cleanly."""

    EXPORT_HEADER = (
        "Date,Description,Amount,Category,Transaction Type,Status,Source,"
        "Engine Rule,Explanation,Manual Override"
    )

    def test_exported_csv_parses(self):
        text = (
            self.EXPORT_HEADER + "\n"
            + '2026-01-05,"AMAZON MARKETPLACE, ORDER 123",-42.00,Office & Equipment,expense,'
            + "Reviewed,engine,office,Matched rule 'office',no\n"
        )
        frame, warnings = _csv(text)
        assert warnings == []
        row = frame.iloc[0]
        assert row["description"] == "AMAZON MARKETPLACE, ORDER 123"
        assert row["amount"] == -42.00
        assert row["imported_category"] == "Office & Equipment"

    def test_edited_export_keeps_category_on_reupload(self):
        # Simulate the full loop at the API level in test_api.py; here we
        # only pin down that the edited values parse.
        text = (
            self.EXPORT_HEADER + "\n"
            + '2026-01-05,"AMAZON MARKETPLACE, ORDER 123",-99.99,Travel,expense,'
            + "Reviewed,manual,,Category set manually during review.,yes\n"
        )
        frame, _ = _csv(text)
        assert frame.iloc[0]["amount"] == -99.99
        assert frame.iloc[0]["imported_category"] == "Travel"


class TestRealWorldStatementLayouts:
    """Bank/card exports are not clean tables. All data is fictional."""

    def test_preamble_lines_above_header_are_skipped_and_reported(self):
        text = (
            "NORTH SHORE CREDIT UNION\n"
            "Account: Chequing 4417\n"
            "Date,Description,Amount\n"
            "2026-03-02,ADOBE CREATIVE CLOUD,-54.99\n"
        )
        frame, warnings = _csv(text)
        assert len(frame) == 1
        assert frame.iloc[0]["date"] == "2026-03-02"
        assert any("above the table header" in w for w in warnings)

    def test_statement_total_and_balance_rows_are_not_transactions(self):
        text = (
            "Date,Description,Amount\n"
            "2026-03-02,ADOBE CREATIVE CLOUD,-54.99\n"
            "2026-03-03,UBER TRIP AIRPORT,-38.20\n"
            ",TOTAL DEBITS,-93.19\n"
            ",Closing Balance,4112.05\n"
        )
        frame, warnings = _csv(text)
        assert len(frame) == 2
        assert list(frame["description"]) == ["ADOBE CREATIVE CLOUD", "UBER TRIP AIRPORT"]
        assert any("statement-total or balance" in w for w in warnings)

    def test_merchant_named_total_is_still_a_transaction(self):
        frame, warnings = _csv("Date,Description,Amount\n2026-03-02,TOTAL FOOD MARKET,-45.20\n")
        assert len(frame) == 1
        assert frame.iloc[0]["description"] == "TOTAL FOOD MARKET"
        assert warnings == []

    def test_repeated_header_row_inside_multipage_export(self):
        text = (
            "Date,Description,Amount\n"
            "2026-03-02,STARBUCKS,-6.75\n"
            "Date,Description,Amount\n"
            "2026-03-03,FIGMA,-15.00\n"
        )
        frame, warnings = _csv(text)
        assert len(frame) == 2
        assert any("repeated header row" in w for w in warnings)

    def test_semicolon_delimited_export_with_decimal_commas(self):
        text = "Date;Description;Amount\n02.03.2026;UBER TRIP;-38,20\n15.03.2026;CAFE;12,50\n"
        frame, warnings = _csv(text, "eu.csv")
        assert list(frame["amount"]) == [-38.20, 12.50]
        assert any("DD/MM/YYYY" in w for w in warnings)

    def test_day_first_dates_inferred_from_unambiguous_row(self):
        text = (
            "Date,Description,Amount\n"
            "02/03/2026,CAFE MILANO,-4.50\n"
            "21/03/2026,BOOK STORE,-19.00\n"
        )
        frame, warnings = _csv(text)
        assert list(frame["date"]) == ["2026-03-02", "2026-03-21"]
        assert any("DD/MM/YYYY" in w for w in warnings)

    def test_ambiguous_dates_default_to_month_first_and_say_so(self):
        text = "Date,Description,Amount\n05/04/2026,CAFE MILANO,-4.50\n06/11/2026,BOOKS,-19.00\n"
        frame, warnings = _csv(text)
        assert list(frame["date"]) == ["2026-05-04", "2026-06-11"]
        assert any("ambiguous between DD/MM/YYYY and MM/DD/YYYY" in w for w in warnings)

    def test_continental_style_file_reads_ambiguous_dates_day_first(self):
        # A file that already writes amounts with a decimal comma and headings
        # in German is not a US export; pairing continental numbers with
        # US dates would mis-date every row.
        text = (
            "Datum;Betrag;Beschreibung\r\n"
            "05.01.2026;-54,99;ADOBE CREATIVE CLOUD\r\n"
            "06.01.2026;1.200,00;ACME DESIGN INVOICE 14\r\n"
        )
        frame, warnings = _csv(text, "sparkasse.csv")
        assert list(frame["date"]) == ["2026-01-05", "2026-01-06"]
        assert list(frame["amount"]) == [-54.99, 1200.00]
        assert any("read as DD/MM/YYYY" in w for w in warnings)

    def test_mixed_date_orders_are_reported_not_silently_resolved(self):
        text = (
            "Date,Description,Amount\n"
            "21/03/2026,BOOK STORE,-19.00\n"
            "03/21/2026,CAFE MILANO,-4.50\n"
        )
        frame, warnings = _csv(text)
        assert len(frame) == 2
        assert any("mixes date orders" in w for w in warnings)

    def test_localized_headers_german(self):
        text = "Datum;Beschreibung;Betrag\n02.03.2026;ADOBE CREATIVE CLOUD;-54,99\n"
        frame, _ = _csv(text, "de.csv")
        assert frame.iloc[0]["description"] == "ADOBE CREATIVE CLOUD"
        assert frame.iloc[0]["amount"] == -54.99

    def test_localized_headers_french_with_accent(self):
        text = "Date de l'opération;Libellé;Montant\n02/03/2026;UBER TRIP;-38,20\n"
        frame, _ = _csv(text, "fr.csv")
        assert frame.iloc[0]["description"] == "UBER TRIP"
        assert frame.iloc[0]["amount"] == -38.20

    def test_unrelated_column_containing_the_word_data_is_not_a_date(self):
        with pytest.raises(ParseError) as excinfo:
            _csv("Card data,Description,Amount\n2026-03-02,STARBUCKS,-6.75\n")
        assert "no date column" in str(excinfo.value).lower()


class TestImportedCategoryMatching:
    def test_canonical_category_tolerates_case_and_punctuation(self):
        from app.services.store import canonical_category

        assert canonical_category("software & subscriptions") == "Software & Subscriptions"
        assert canonical_category("  REFUND/CREDIT ") == "Refund / Credit"
        assert canonical_category("Travel") == "Travel"

    def test_canonical_category_refuses_unknown_labels(self):
        from app.services.store import canonical_category

        assert canonical_category("Office Supplies") is None
        assert canonical_category("Adobe") is None
        assert canonical_category("") is None

    def test_lowercase_category_from_spreadsheet_survives_round_trip(self):
        frame, warnings = _csv(
            "Date,Description,Amount,Category,Status\n"
            "2026-03-02,STARBUCKS COFFEE,-6.75,meals & entertainment,Reviewed\n"
        )
        assert warnings == []
        assert frame.iloc[0]["imported_category"] == "meals & entertainment"


class TestShippedSampleFiles:
    """Sample data is documentation: it must keep parsing the way README says."""

    def test_every_csv_sample_parses(self):
        import pathlib

        samples = sorted((pathlib.Path(__file__).parent.parent / "sample_data").glob("*.csv"))
        assert samples, "no sample CSVs shipped"
        for path in samples:
            frame, warnings = parse_statement(path.read_bytes(), path.name)
            assert len(frame) >= 10, path.name
            assert set(frame.columns) >= {"date", "description", "amount"}, path.name

    def test_messy_sample_keeps_preamble_totals_out_of_the_ledger(self):
        import pathlib

        path = (
            pathlib.Path(__file__).parent.parent
            / "sample_data"
            / "sample_messy_designer.csv"
        )
        frame, warnings = parse_statement(path.read_bytes(), path.name)
        descriptions = set(frame["description"])
        assert "TOTAL DEBITS" not in descriptions
        assert "CLOSING BALANCE" not in descriptions
        # A merchant really named TOTAL… is still a transaction.
        assert "TOTAL FOOD MARKET CATERING" in descriptions
        assert all("DD/MM/YYYY" not in w or "day-first" in w for w in warnings)
