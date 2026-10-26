# StatementIQ

Deterministic bank and credit-card statement categorizer for freelancers and
small businesses. Upload a CSV or JSON statement, review the automatically
categorized transactions, correct the uncertain ones, and export the result.

The worked example is a **graphic designer's** card and bank statement:
client invoices, Adobe and font subscriptions, a Wacom tablet, stock assets,
print shop charges, conference tickets, and transfers between their own
accounts.

Every classification comes from an **auditable rule table**, not a model.
No LLM or ML library is used for categorization — `backend/tests/test_brain.py`
contains an AST guard that fails the suite if an AI/MLOps import ever appears
in the engine module.

## Stack

| Layer    | Technology                                                                            |
| -------- | ------------------------------------------------------------------------------------- |
| Backend  | Python 3.12 · FastAPI · Pandas · Uvicorn                                              |
| Engine   | `backend/app/engine/brain.py` — ordered regex/keyword rule table                      |
| Parsing  | `backend/app/services/parser.py` — stdlib `csv` tokenizer + name-based column mapping |
| Frontend | React 18 · Vite 5 · Tailwind CSS 3.4 (design-token violet/ink UI)                     |
| Tests    | pytest — 133 tests (parser, engine, financial totals, API, export round-trip)         |
| Ops      | Docker images, docker-compose, GitHub Actions CI                                      |

## Project layout

```
statementiq/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint (env-configured CORS, router)
│   │   ├── models.py          # Pydantic schemas
│   │   ├── api/routes.py      # /api endpoints: upload, fetch, override
│   │   ├── engine/brain.py    # THE BRAIN — deterministic rule engine
│   │   └── services/
│   │       ├── parser.py      # CSV/JSON parsing, column mapping, sign rules
│   │       └── store.py       # In-memory sessions, financial semantics
│   ├── sample_data/           # Synthetic statements: clean, JSON, and a
│   │                          # deliberately messy European card export
│   ├── tests/                 # test_parser, test_brain, test_api, test_review_flow
│   ├── requirements.txt       # runtime deps only
│   └── requirements-dev.txt   # + pytest, httpx
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Landing → upload → review orchestration
│   │   ├── api.js             # Fetch wrapper for the backend
│   │   ├── lib/demoData.js    # Fictional demo statement + downloadable sample
│   │   ├── lib/exportCsv.js   # CSV/JSON export builders
│   │   └── components/        # Landing, Navbar, FileDropzone, SummaryCards,
│   │                          # ReviewToolbar, TransactionsTable, CategoryTotals,
│   │                          # DetailsPanel, StatusBadge
│   └── package.json
├── docker/                    # backend.Dockerfile, frontend.Dockerfile, nginx.conf
├── .github/workflows/ci.yml   # pytest + frontend build + image builds
├── docker-compose.yml
├── .env.example               # documents every variable the code actually reads
├── README.md
├── DESIGN.md                  # Pipeline, rule precedence, financial conventions
└── AI_USAGE.md                # What AI helped with, and what it got wrong
```

## Quickstart

### 1. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # runtime + test deps
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

API docs at http://localhost:8000/docs · health check at `/api/health`
(reports `llm_used: false`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to port 8000.

Production build: `npm run build` (output in `frontend/dist`).

### 3. Tests

```bash
cd backend
.venv/bin/python -m pytest tests -q      # 133 passed
```

The frontend has no separate lint or type-check step; `npm run build` is the
verification used here (it compiles every JSX module).

### 4. Containers

```bash
docker compose up --build     # app on http://localhost:8080, nginx proxies /api
```

`docker/backend.Dockerfile` runs Uvicorn as an unprivileged user with an
`/api/health` healthcheck; `docker/frontend.Dockerfile` is a two-stage
`npm run build` → nginx image that serves the SPA and proxies `/api` to the
backend service.

### 5. Configuration

Copy `.env.example` and set only what you need — every variable listed there
is read by the code:

| Variable            | Read by                            | Default when unset            |
| ------------------- | ---------------------------------- | ----------------------------- |
| `CORS_ORIGINS`      | `app/main.py`                      | localhost ports 5173 and 4173 |
| `MAX_UPLOAD_BYTES`  | `app/api/routes.py`                | 10485760 (10 MB)              |
| `VITE_API_BASE_URL` | `frontend/src/api.js` (build time) | same-origin `/api`            |

`MAX_UPLOAD_BYTES` is the authoritative limit and the server rejects anything
larger with a readable 413. The dropzone repeats the 10 MB default locally so an
oversized file fails instantly instead of after an upload; if you deploy a
larger limit, raise `MAX_BYTES` in `frontend/src/components/FileDropzone.jsx`
in the same change.

There are no secrets in this project: nothing is sent to a third party, so
there are no API keys to configure or to accidentally commit.

### 6. Try it without a file

The upload screen offers **Try demo data** (fictional March 2026 statement,
processed through the real pipeline) and **Download sample CSV**. The same demo
is linkable: open `http://localhost:5173/?demo=1` to land directly in the
review dashboard.

`backend/sample_data/sample_messy_designer.csv` is a deliberately awkward
export — bank preamble, `;` delimiters, decimal commas, DD/MM dates, a
repeated header mid-file, totals/balance footer rows, an opaque POS line, a
dispute debit and a merchant called "TOTAL FOOD MARKET". Uploading it
demonstrates every layout rule in the parser at once, and CI asserts it still
parses.

## Supported input formats

### Column mapping

Columns are matched **by name**, so order and extra columns do not matter.
Header matching is case-insensitive, **accent-insensitive** (`BESCHREIBUNG`,
`Libellé`, `Descripción` all match), and ignores spaces, underscores, hyphens,
slashes, parentheses and dots plus French/Italian apostrophes (`Date de
l'opération` → `date de lopration`). A UTF-8 BOM is stripped.

| Concept     | Recognized headers                                                                                                                                                                                                   |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Date        | `Date`, `Transaction Date`, `Posted/Posting Date`, `Value Date`, `Paid On`, `Date Paid`, `Transaction Time`, `Booking Date`, `Datum`, `Fecha`, `Date de l'opération`, `Data Transazionale`, `Data` (exact cell only) |
| Description | `Description`, `Payee`, `Merchant`, `Merchant Name`, `Memo`, `Narrative`, `Details`, `Transaction/Card Description`, `Beschreibung`, `Omschrijving`, `Libellé`, `Descrizione`, `Descripción`, `Purpose`              |
| Amount      | `Amount`, `Transaction Amount`, `Value`, `Betrag`, `Bedrag`, `Importo`, `Importe`, `Montant`                                                                                                                         |
| Debit       | `Debit(s)`, `Withdrawal(s)`, `Money Out`, `Paid Out`, `Outflow`, `Soll`, `Addebito`, `Uitgave`, `Cargo` (exact cell only)                                                                                            |
| Credit      | `Credit(s)`, `Deposit(s)`, `Money In`, `Paid In`, `Inflow`, `Haben`, `Accredito`, `Ontvangst`, `Abono`                                                                                                               |
| Category    | `Category`, `Tax Category`, `Assigned Category`, `Categorie`, `Categoria`                                                                                                                                            |
| Status      | `Status`, `Review Status`                                                                                                                                                                                            |

Date, Description and one of Amount / Debit / Credit are required. Anything
else in the file is ignored. Exact alias matches win over substring matches,
and already-claimed columns are excluded — so a `Value Date` column can never
be mistaken for a `Value` (amount) column, and a `Card data` / `Cargo`-like
word inside an unrelated header cannot create a phantom date or debit column.

### Real statement layouts

Bank exports rarely start with a header row. The parser handles the messy
versions explicitly instead of giving up:

- **Preamble lines** (bank name, account number, run date) above the table are
  skipped, and the upload warning says how many lines were skipped and quotes
  the first few.
- **Delimiter detection** tries `,`, `;`, tab and `|` until one produces a
  usable header — the first line of a preamble file carries no delimiter, so
  sniffing line 1 is not enough.
- **Repeated headers** from multi-page exports are recognized and dropped, with
  a count reported.
- **Totals and balance footers** (`TOTAL DEBITS`, `Closing Balance`,
  `Page 2 of 4`, …) are dropped as non-transactions, with a count reported. The
  footer pattern is anchored, so a merchant actually called
  `TOTAL FOOD MARKET` stays a transaction.
- **European formats**: `;`-delimited files with decimal commas (`-38,20`) are
  normalized, and `1.234,56` thousands dots parse correctly.
- **Date order**: `03/04/2026` is ambiguous, so the file's own evidence decides.
  A day-first column (a row like `17/03/2026` can only be day-first) is parsed
  as DD/MM and reported; a strictly month-first column is parsed as MM/DD and
  reported; a file whose rows are all ambiguous is read as MM/DD **and warns**,
  unless it already writes numbers or headings the continental way (`;`/`|`
  delimiters, `Datum`/`Beschreibung`), which is read as DD/MM and says so;
  a file that contradicts itself ("'21/03/2026' is day-first but '03/21/2026' is
  month-first") says so instead of quietly picking the majority. Every one of
  these cases is reported in the UI rather than being hidden, and the numeric
  `d/m/y` family is resolved by this code rather than left to a date library's
  guess.

`TOTAL DEBITS` rows are never imported as transactions, but they are also
never used to "fix" the ledger: totals are recomputed from the transactions the
parser actually accepted.

### CSV compatibility

Quoted fields, escaped double quotes (`""`), commas and newlines inside
descriptions (`"AMAZON MARKETPLACE, ORDER 123"`), LF / CRLF / CR line endings,
blank lines, empty optional cells, negative and decimal amounts, currency
symbols and thousands separators (`$12,345.67`), trailing-minus (`12.34-`) and
parenthesized (`(12.34)`) negatives.

### Sign convention

Expenses, withdrawals and debits are **negative**; income, deposits and
credits are **positive**.

- `Amount` column: used as-is.
- `Debit`/`Credit` (or `Withdrawal`/`Deposit`, `Money Out`/`Money In`):
  normalized amount = `credit − debit`.
- If a file has **both** an `Amount` column and debit/credit columns, `Amount`
  takes precedence. Nothing is counted twice, because each row yields exactly
  one transaction regardless of how many amount columns exist.
- Amounts are never silently flipped: if a sign cannot be derived, the row is
  reported with its line number.

### Error reporting

Rows whose field count does not match the header are **rejected with their
line number** and surfaced as warnings in the UI — for example:

> Row 19 was skipped: it has 10 fields but the header has 7. Check the
> quotation marks and commas in that row.

Valid rows still import; nothing is silently discarded, and `on_bad_lines="skip"`
is not used. Invalid dates/amounts raise a readable message naming the row.
Raw stack traces stay in the server log.

### JSON

A top-level array of transaction objects, or an object wrapping one under
`transactions`, `data`, `items` or `rows`. The same alias and sign rules apply.

## Export format

Downloaded from the dashboard header as CSV or JSON.

CSV — header plus one line per transaction, **exactly 10 fields on every
line**, no summary footer:

```
Date,Description,Amount,Category,Transaction Type,Status,Source,Engine Rule,Explanation,Manual Override
```

Fields containing commas, quotes or newlines are quoted and inner quotes are
doubled. A UTF-8 BOM is prepended so Excel opens descriptions correctly.

JSON uses schema `statementiq.export/v1` with `statement` (summary, including
`by_category`) and `transactions` (`id`, `date`, `description`, `amount`,
`category`, `transaction_type`, `status`, `source`, `matched_rule`,
`explanation`, `original_category`, `manually_overridden`, `source_row`).

**Round trip:** edit any exported cell and re-upload the file. The parser
recognizes the exported headers, and `Category` values are kept only when they
are valid categories from the taxonomy — anything else (including
`Uncategorized`) falls back to the rule engine. Imported categories are
labelled in the UI so they are never mistaken for freshly computed ones.

`Category` is the only instruction the importer reads. `Date` and `Amount` are
re-validated and feed the totals as usual, and rows are duplicate-checked again,
but `Status`, `Source`, `Engine Rule` and `Explanation` are audit trail for the
spreadsheet: a preserved `Category` comes back as `Reviewed` with
`source=imported` no matter what those cells say. To push a row back through the
engine, blank its `Category` (or set a value outside the taxonomy).

## API

| Method  | Path                                        | Purpose                                                                              |
| ------- | ------------------------------------------- | ------------------------------------------------------------------------------------ |
| `POST`  | `/api/statements`                           | Upload a statement (multipart `file`); returns `summary`, `transactions`, `warnings` |
| `GET`   | `/api/statements/{id}`                      | Re-fetch a processed statement                                                       |
| `PATCH` | `/api/statements/{id}/transactions/{tx_id}` | Manually reassign a category (marks the row reviewed)                                |
| `GET`   | `/api/categories`                           | Category vocabulary for the UI dropdowns                                             |
| `GET`   | `/api/health`                               | Liveness + engine identity (`llm_used: false`)                                       |

## Dashboard

- Summary cards: transactions, expenses (excluding transfers), income
  (business income + interest only), refunds, net cash flow, and items needing
  review — the warning card toggles a review-only filter.
- Search by description, category and status filters, date/amount sorting,
  pagination (12 rows per page).
- Inline category dropdowns on flagged and manually/imported rows; a details
  slide-over showing the matched rule, its plain-English explanation, the
  provenance (engine / imported / manual) and the **source row** in the uploaded
  file (`#19`) so any number can be traced back to the statement.
- **Totals by category** in a sticky sidebar, sorted by absolute amount with a
  proportional bar per category; clicking a row filters the table to it. This is
  the "total for each category" the brief asks for, and it recomputes live as
  rows are re-categorized.
- **Review progress** bar: reviewed vs total, so it is obvious when a statement
  is actually finished.
- Categorization is a bookkeeping aid, not tax advice — stated in the UI.

## Notes & limitations

- Statements live in server memory only and are lost on restart. Uploaded bytes
  are held in RAM during parsing, never written to disk, and are not forwarded
  to any third party.
- Parsing is synchronous and single-worker, so the upload limit is also a
  response-time limit. Measured on the development machine used here: a
  synthetic 7.2 MB / 200,000-row statement parses, categorizes and returns in
  about 20 s through nginx. Typical statements (a few hundred rows) take well
  under a second.
- The rule table ships with common freelancer/small-business merchants, tuned
  for the designer persona in the sample data. Extend it by adding `Rule`
  entries in `brain.py` — list order is precedence.
- Unknown merchants and opaque POS descriptions stay in **Needs Review**; the
  engine does not guess. The same applies to chargeback/dispute debits, whose
  merchant text describes the _disputed purchase_, not the money movement.
- Refund-to-original-expense linking uses the matched merchant rule's category;
  it does not search the ledger for the originating charge.
- Duplicate detection is same-day, same-normalized-description, same-amount.
  Suspicious pairs are flagged, never removed.
- The parser reports everything it skips; it does not reconcile against the
  statement's own printed totals.

See `DESIGN.md` for the decision policy and `AI_USAGE.md` for the no-LLM
categorization constraint.

## Screenshots

### Landing Page

![StatementIQ Landing Page](screenshots/landing%20page.png)

### New Statement

![Create a New Statement](screenshots/new%20statement.png)

### Try Demo

![StatementIQ Demo](screenshots/try%20demo.png)
