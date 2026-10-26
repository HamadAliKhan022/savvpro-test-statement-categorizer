# StatementIQ — Design

## 1. Use case

Freelancers and small businesses export monthly bank/card statements and
then spend hours pasting rows into spreadsheets to sort them into
tax-relevant buckets (software, travel, meals, client income…). Generic
"AI categorizers" guess at categories with opaque models — which is exactly
the wrong property for something that feeds a tax filing. A wrong guess is
invisible; a rule miss is visible.

**StatementIQ's thesis:** categorization should be *deterministic,
explainable, and fail-safe*. The same input must always produce the same
category, every decision must name the rule that produced it, and anything
the system does not recognize must be escalated to a human as **Needs
Review** rather than guessed.

**Chosen customer:** freelance graphic designers and small design studios.
Their statements mix client invoices and Stripe/Square payouts with Adobe and
font subscriptions, drawing tablets and art supplies, stock assets and print
shop charges, conference tickets, home-office rent, mileage-like rideshare
trips, refunds, and transfers to their own savings — a vocabulary narrow
enough to write explicit rules for and wide enough to be genuinely messy.

### Primary user flow

1. Land on the marketing page, or go straight to upload; drag & drop a
   CSV/JSON statement (or load the fictional demo statement).
2. The parser tokenizes and normalizes rows; the Decision Engine classifies
   every row in one pass; duplicates are flagged.
3. The dashboard shows summary cards and a warning badge for flagged rows.
4. The user searches/filters/sorts, opens a row to read *why* it was
   categorized, and reassigns categories inline.
5. A reassigned row becomes `Reviewed`, keeps an audit trail of its original
   engine category, and updates the totals immediately.
6. The user exports CSV/JSON, edits it in a spreadsheet, and re-uploads it —
   the same app must consume its own output.

## 2. Architecture

Stages are deliberately separated so each is testable on its own:

```
Browser (React + Tailwind)
   │  multipart upload / JSON PATCH / client-side export
   ▼
FastAPI  ── app/api/routes.py        HTTP layer + import-policy decisions
   │
   ├── app/services/parser.py        1. parse + 2. normalize
   │        (csv tokenizer, column aliasing, date/amount coercion,
   │         debit/credit → signed amount, row-level rejection warnings)
   │
   ├── app/engine/brain.py           3. categorize + 4. type detection
   │        (regex rule table, refund guard, duplicate keys;
   │         pure — no I/O, no network, no models)
   │
   └── app/services/store.py         5. financial semantics + sessions
            (categories, statuses, source labels, summary arithmetic)

Frontend src/lib/exportCsv.js        6. export (documented, re-uploadable)
```

Data flow: `bytes → DataFrame(+warnings) → Transaction[] → summary → export`.
Each arrow is covered by tests, and the last arrow feeds back into the first
(`test_export_then_reupload_is_lossless`).

The brain is a pure function: `categorize(description, amount) -> Decision`.
It imports only `re` and `dataclasses`, which makes the no-AI constraint
trivially auditable (a test parses the module's AST and fails if any AI
library is ever imported). The engine has no imports from FastAPI, Pandas or
React-side code, so it stays independent of the delivery layer.

### 2.1 Parsing strategy

CSV is tokenized with the standard-library `csv` module, not a
field-count-assuming reader. That alone fixes commas/escaped quotes/newlines
inside quoted values and LF/CRLF/CR endings. Real exports then need three more
things, which is where the "messy statement" work lives:

- **The delimiter is tried, not sniffed from line 1.** `,`, `;`, tab and `|`
  are each tokenized until one produces a usable header. Preamble lines (bank
  name, account number, run date) usually contain no delimiter at all, so
  sniffing the first line picks the wrong answer for exactly the files that
  need it most.
- **The header row is found, not assumed.** The first 25 tokenized rows are
  tested for recognizable columns; the skipped preamble is reported with its
  content, and a header repeated mid-file (multi-page exports) is dropped and
  counted.
- **Footer rows are excluded, with an anchored pattern.** `TOTAL DEBITS`,
  `Closing Balance`, `Page 2 of 4` and friends are not transactions. The regex
  is anchored to the whole cell so a merchant genuinely named
  `TOTAL FOOD MARKET` stays a transaction — the test pins both directions.

Column handling:

- **Column matching by name.** Headers are canonicalized (lowercased, accents
  folded away via NFKD, apostrophes dropped, spaces/underscores/hyphens/
  slashes/parentheses/dots collapsed) and matched against alias tables, so
  `Libellé`, `BESCHREIBUNG` and `Date de l'opération` behave like their English
  equivalents. Order and extra columns are irrelevant. A BOM is stripped via
  `utf-8-sig`.
- **Exact-only aliases** exist for words that are also ordinary English inside
  other headers: `data` (Italian for "date") and `cargo` (Spanish for "debit")
  only match a column whose *entire* header is that word, so `Card data` can
  never become a date column.
- **Deterministic resolution.** Assignment runs date → description → amount →
  debit → credit → category → status. Exact alias matches beat substring
  matches, earlier aliases beat later ones, and already-claimed column indices
  are excluded. The exclusion set is why `Value Date` can never be read as a
  `Value` (amount) column.
- **One amount per row.** `Amount` wins if present; otherwise the amount is
  `credit − debit`. Since each row produces exactly one transaction, files
  carrying both shapes cannot double-count. `;`/`|` files are read with decimal
  commas (`-38,20`) and `1.234,56` thousands dots.
- **Date order is decided from the file's evidence, then said out loud.**
  `d/m/y` numeric dates are resolved here rather than delegated to a date
  library's per-value guess: a day-first sample (`17/03/2026`) means DD/MM for
  the whole file, a month-first sample means MM/DD, an all-ambiguous file is
  read as MM/DD *with a warning* — unless its amounts or headings are already
  continental (`;`/`|` delimiters, `Datum`, `Beschreibung`), because pairing
  decimal-comma numbers with US dates would mis-date every row — and a
  self-contradictory file is reported as
  mixed. Whichever reading is chosen, the user is told which example forced it.
- **`YYYY-MM-DD` never reaches a date library.** It is the most common spelling
  in bank exports and the only one with no order ambiguity, so it is resolved
  with the standard library. Delegating it per value to `pandas.to_datetime`
  re-guesses the format on every row, which cost ~1.3 ms per row and made a
  file that is legal under the 10 MB limit exceed the proxy timeout. Other
  spellings (`Jan 5, 2026`, `5.1.2026`) still take the general path, and an
  impossible date such as `2026-02-30` fails there exactly as it did before.
- **Recovery without silence.** A row whose field count differs from the
  header is skipped *and reported by line number*, and the rest of the file
  still imports. `on_bad_lines="skip"` is never used, because it hides the
  damage. Unparseable dates/amounts raise a `ParseError` naming the row.
  Stack traces stay in server logs; users get actionable sentences.

## 3. The Decision Engine ("The Brain")

### 3.1 Normalization

The raw description is lowercased, punctuation replaced with single spaces,
and whitespace collapsed (`"MSFT*OFFICE 365"` → `"msft office 365"`). Rules
are written against plain word tokens, so they never break on merchant
decoration like `*`, `#`, or store numbers.

### 3.2 Rule table

`RULES` is an **ordered list** of rules; each rule carries:

| Field     | Meaning |
|-----------|---------|
| `name`    | Stable id surfaced in the UI as provenance (e.g. `client_income`) |
| `category`| Tax category assigned on match |
| `pattern` | Compiled regex of keyword alternatives, anchored on word boundaries (`(?:^|\s)…(?:\s|$)`) so "aws" matches the token, not a substring of "laws" |
| `polarity`| `expense` (negative amounts), `income` (positive), or `any` |

**First match wins**, so ordering encodes priority. Specific rules precede
generic ones — e.g. the `bank_fees` rule (`monthly service fee`) sits
before `software` (`monthly service`) so a bank fee is never swallowed by a
subscription keyword, and `design_assets` (`adobe stock asset`) sits before
`software` because purchased assets are marketing/material spend, not a tool
subscription.

### 3.3 Sign policy (income vs expense)

- `amount < 0` → expense candidate.
- `amount > 0` → income candidate: client payments, payouts, and interest
  rules match only with `polarity="income"`.
- **Refund guard:** if a positive amount matches an *expense* rule, the
  result is rewritten to `Refund / Credit`, the reason names the merchant
  rule it matched and the expense category it is associated with. A positive
  amount can therefore never land in an expense category, and a refund is
  never booked as income.
- **Contradictions are not guessed:** a "refund" keyword on a negative
  amount fails the income-polarity check, and the refund rule stops the
  scan there so no later merchant rule can claim the sign — e.g.
  `UBER TRIP REFUND, -25.00` is Needs Review, while `UBER TRIP, -25.00` is
  Travel.
- Merchant recognition is *not* business-relevance. Matching `uber` proves
  which vendor was paid, not that the spend is deductible; the category is a
  bookkeeping label and the UI says so.

### 3.4 Rule precedence

`RULES` is an ordered list and the **first match wins**, so the list *is* the
precedence document. Conflicts resolve deterministically:

1. Specific before generic (`bank_fees` before `software`).
2. Polarity filter applied per rule, so an income-only rule cannot fire on a
   debit.
3. Refund guard rewrites at the end, never mid-scan.
4. Nothing matched → Needs Review, with the reason naming the cause.

Reordering the list changes behaviour visibly, and the tests pin the
precedence-sensitive pairs.

### 3.5 Uncertainty and duplicates

A row is flagged `Needs Review` (category `Uncategorized`) when:

1. The description is empty, or is pure card-terminal noise
   (`POS PURCHASE #88421`) — detected by an opacity regex *before* rule
   matching, because such strings contain digits that could spuriously
   match nothing useful.
2. It is a chargeback or dispute debit (`DISPUTE - ELECTRONIC ARTS`): the
   merchant text names the *disputed purchase*, not what this money movement
   is, so the row is refused rather than booked as Marketing or Software. A
   `CHARGEBACK FEE` is still a bank fee, and a won dispute is still a
   `Refund / Credit` — the guard only fires on the negative leg.
3. No rule in the table matches.
4. It looks like a duplicate: `find_duplicate_pairs` keys on
   (date, normalized description, amount rounded to cents) and flags the
   *second* occurrence, recording the first row's number. Duplicates are
   **kept and flagged**, never deleted — only a human can decide whether a
   repeat charge was intentional.

The reason string states exactly which case occurred. Flagged rows render
with amber badges and inline dropdowns so a human resolves them in seconds.

### 3.6 Transactions and transfers

Recurring card-payment network artefacts and internal account moves match the
`Transfers & Internal` rule. They are excluded from expenses and from income
so that moving money between your own accounts cannot inflate either side of
the report.

## 4. Financial calculation conventions

Defined once in `app/services/store.py` and used by every summary, so the
cards and the export always agree:

| Metric | Definition |
|--------|-----------|
| Income | `Business Income` + `Interest Income` with positive amounts. Refunds and transfers are excluded. |
| Refunds | `Refund / Credit` totals, reported as their own line — never folded into income or expenses. |
| Expenses | Sum of negative amounts in every category **except** `Transfers & Internal`. |
| Transfers | `Transfers & Internal` totals, shown separately. |
| Net cash flow | Sum of all normalized amounts (the only figure where every row counts). |
| Needs review | Count of rows with status `Needs Review`. |

Manual corrections and preserved imported categories recompute all of the
above on the same request, so totals can never lag behind the table.

## 5. Import policy for previously categorized files

The app consumes its own exports, which means an uploaded file can arrive with
a `Category` column already filled in. Policy (implemented in
`app/api/routes.py`):

- A non-empty imported category is preserved **only** if it is an exact member
  of the taxonomy and is not `Uncategorized`; the transaction is recorded with
  `source = "imported"` and reason "Category imported from the uploaded file
  (previously reviewed)."
- Anything else — typos, spreadsheet formulas, categories from another tool —
  is discarded and the engine decides, with `source = "engine"`. Metadata in
  the file never overrides the rules.
- Imported rows are still duplicate-checked, so a re-uploaded file cannot smuggle
  past a flag.
- `Category` is the only instruction the importer reads. `Status`, `Source`,
  `Engine Rule` and `Explanation` exist for whoever edits the spreadsheet, and a
  preserved category is recorded as `Reviewed`/`imported` regardless of what
  those cells say; date and amount are still validated like any other row.
- Every transaction carries a provenance label shown in the UI: `engine`,
  `imported` or `manual`. Imported and manual rows expose an editable dropdown
  so their status is explicit rather than implied.
- Manual correction (`PATCH /api/statements/{id}/transactions/{tx}`) sets the
  category, marks the row `Reviewed`, switches `source` to `manual`, records
  `original_category` for audit, and returns recomputed totals in the same
  response — so the dashboard can never lag behind the table.
- Dates and amounts are validated identically regardless of category presence;
  categorization metadata grants no parsing exemption.

## 6. Export behaviour

CSV: header plus one line per transaction, exactly 10 fields per line,
`Date, Description, Amount, Category, Transaction Type, Status, Source,
Engine Rule, Explanation, Manual Override`. No summary footer — the earlier
footer (10 fields under a 7-column header) was the root cause of the
"Expected 7 fields in line 19" failure. Fields are quoted when they contain a
comma, quote or newline, inner quotes are doubled, and a UTF-8 BOM is added for
Excel.

JSON: schema `statementiq.export/v1`, with statement metadata and per-row
`category`, `status`, `source`, `matched_rule`, `explanation`,
`original_category`, `manually_overridden`.

Round trip is verified by tests: build the export from processed rows, upload
that text back, and assert identical (date, description, amount, category) sets
with zero parse warnings.

## 7. UI design

The interface is built on a small set of **design tokens**, not one-off utility
strings, so the landing page and the dashboard cannot drift apart:

- `tailwind.config.js`: a violet `brand` ramp (`50 #f5f3ff … 500 #8155f7 ·
  600 #6d38eb · 700 #5b26cf …`), a near-black `ink` ramp for text and dark
  sections, `2xs` type step, `label` letter-spacing, four elevation shadows
  (`card`, `panel`, `float`, `glow`), `4xl` radius, a spring easing curve and
  `fade-in` / `slide-in` / `shimmer` keyframes.
- `src/index.css`: `@layer components` classes (`.card`, `.panel`, `.btn`,
  `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.chip`, `.field`, `.label`,
  `.num`, `.skeleton`) plus `.grid-pattern` / `.dot-pattern` utilities. Body
  text uses tabular numerals and `cv11`/`ss01` opentype features so figures in
  money columns align; a single global `:focus-visible` ring gives every
  control the same keyboard affordance.
- Neutrals come from `zinc` and hairline borders use `black/[0.06]` rather than
  a fixed gray, so separators stay subtle on both light and dark surfaces.

Screens:

- **Landing** (`components/Landing.jsx`): dark sticky nav over an `ink-900`
  hero with the grid pattern and one brand glow, the deterministic-equals-safe
  positioning, and a product mock in browser chrome that overlaps the hero
  boundary — its rows and KPI tiles are the real numbers the demo statement
  produces through the live API, captioned "Illustrative data shown". Then How
  It Works, a six-slot bento of features (each naming the actual rule ids), a
  Security section describing real behaviour (own backend, RAM only, nothing to
  disk, no third party, no LLM) including the restart caveat, a closing CTA and
  a footer. Every button leads somewhere functional.
- **Upload**: drag & drop plus file picker, supported formats and expected
  columns, downloadable sample CSV, Try-demo button, size/validation feedback,
  and parser warnings in an amber banner that lists each skipped line, footer
  row, and the date-order decision.
- **Review dashboard**: six summary cards (the review card is a clickable
  filter) over a two-column layout — the table on the left, a sticky sidebar on
  the right holding the **review progress** bar and **Totals by category**
  (every category with its count, a proportional bar, and a click that filters
  the table to it). Search + category/status filters + date/amount sorting +
  12-row pagination, inline category dropdowns on rows needing attention, and a
  right-hand **details slide-over** (`DetailsPanel.jsx`) with the matched rule,
  the plain-English reason, provenance (`engine` / `imported` / `manual`), the
  source line number in the uploaded file, and the not-tax-advice disclaimer.
  Keyboard-reachable: Escape closes the panel, `aria-pressed` marks active
  filters, the totals rows and the progress bar expose `aria-pressed` /
  `role="progressbar"`.

The slide-over replaced a centered modal: reviewing 20–400 rows is a reading
task, and keeping the table visible while the explanation opens beside it is
what makes the "needs review" queue fast to drain.

## 8. Production scaffolding

- `docker/backend.Dockerfile` — slim Python 3.12, runtime requirements only,
  unprivileged user, `/api/health` healthcheck, Uvicorn on 8000.
- `docker/frontend.Dockerfile` — `npm ci` + `npm run build` in stage one,
  nginx 1.27-alpine serving `dist/` in stage two, with `docker/nginx.conf`
  proxying `/api` to the backend service, hashed assets cached immutably, the
  HTML shell `no-store`, and a body-size limit matching the API's.
- `docker-compose.yml` — two services; the app is reachable on `:8080` and the
  browser never needs a second origin, so CORS is not part of the happy path.
- `.github/workflows/ci.yml` — pytest on 3.12 and the Vite production build in
  parallel, then both images build once those pass.
- `.env.example` documents only the three variables the code reads
  (`CORS_ORIGINS`, `MAX_UPLOAD_BYTES`, `VITE_API_BASE_URL`). There are no
  secrets anywhere in the project — no provider keys exist to leak, because no
  provider is called.

## 9. Deliberate limitations

- **In-memory store:** statements vanish on restart. A persistence layer
  (SQLite/Postgres) is the natural next step; the API surface already fits.
- **Static rule table:** coverage is only as good as its keywords. The
  extension path is adding rules — never model calls.
- **No amount heuristics:** the engine never uses spend-size priors
  ("$12 must be lunch"). Determinism beats cleverness here.
- **Refund association is rule-based:** the category a refund is associated
  with comes from the matched merchant rule, not from finding the original
  charge in the ledger.
- **Ambiguous files are reported, not mapped:** there is no interactive
  column-mapping UI; when required columns cannot be identified the parser
  names what it found and what it expected.
