# AI Usage Policy — StatementIQ

## The hard constraint

**No external LLMs or AI models (GPT, Claude, Gemini, or otherwise) may be
used for transaction categorization decisions — at runtime or in the
engine's dependency graph.**

This is a product requirement, not a preference. StatementIQ exists because
tax categorization needs to be deterministic, explainable, and auditable.
Every classification is produced by `backend/app/engine/brain.py`: a pure
Python module that imports only `re` and `dataclasses` and evaluates an
ordered regex/keyword rule table.

## How the constraint is enforced

1. **Isolation by design** — the engine is a pure function
   (`categorize(description, amount) -> Decision`) with no I/O, no network
   access, and no model artifacts.
2. **AST guard test** — `backend/tests/test_brain.py::TestNoLLMConstraint`
   parses `brain.py`'s syntax tree and fails the suite if any import from a
   known AI/ML library (`openai`, `anthropic`, `google.generativeai`,
   `langchain`, `transformers`, `torch`, `tensorflow`, `sklearn`, …) ever
   appears.
3. **Fail-safe over guess** — anything the rules cannot resolve becomes
   `Needs Review` for a human, so the system never needs probabilistic
   fallback behavior.
4. **Public signal** — `/api/health` reports
   `{"engine": "deterministic-rule-engine-v1", "llm_used": false}` and the
   UI shows a "Rule engine only · No LLMs" badge.

Note: merchant names such as `openai` or `anthropic` appear in the rule
table as *keywords to match* (they are expenses a freelancer might pay).
Matching a merchant by string is not calling a model.

## Where AI *was* used

**Tool:** Qoder (agentic coding assistant, this IDE).

**What it helped with**

- Scaffolding the FastAPI app, the React/Vite/Tailwind frontend, and the
  pytest suite.
- The `brain.py` rule table, the CSV/JSON parser rewrite (alias tables,
  `csv`-module tokenization, debit/credit normalization), duplicate detection,
  and the refund guard.
- This pass: header-row discovery, delimiter trial, footer rejection,
  accent-folded localized headers, day-first inference, the designer persona
  rules, the chargeback guard, `source_row` traceability, the Tailwind design
  tokens and every dashboard component (summary cards, category-totals
  sidebar, review progress, details slide-over), and the landing page — which
  was written by a delegated Qoder sub-agent from a written brief and then
  reviewed, rebuilt and browser-checked here like any other file.
- README.md, DESIGN.md, this file, the Dockerfiles, nginx config, the compose
  file and the CI workflow.

**What it was never used for:** inference at runtime, embeddings, training
data, or any model call inside the categorization path. Verification was
local: **133 pytest tests pass** (`.venv/bin/python -m pytest tests -q`) and
`npm run build` succeeds. End-to-end flows were driven in a real browser
against the running dev servers — landing page → demo upload → KPI cards →
filter/pagination → details panel → export CSV/JSON → re-upload the edited
export. The CSV round trip was additionally exercised against the live API
with a hand-written export-format file containing quoted commas, CRLF
endings, and edited categories. The containerized stack was verified by
building both images and uploading a real sample file through nginx.

The most recent pass was a self-audit against the brief, and it produced the
numbers claimed above plus three findings the earlier verification had missed.
The audit scripts are not part of the repo (they live outside it); what is
recorded here is what they measured:

- **Behaviour:** 33 assertions against the running API — each expectation
  computed from the fixture text or the documented sign policy, not read back
  from the code — passed both directly on the dev server and through nginx in
  the compose stack.
- **Export round trip:** the shipped `exportCsv.js` was imported directly,
  its output re-uploaded, and the totals compared before and after.
- **Browser workflow:** 24 checks at a 390×844 viewport, driven over the
  DevTools protocol against a real Chromium — upload, KPI cards, card list
  instead of table, details slide-over, category edit propagating to the
  sidebar and KPIs, the actual CSV download, and re-upload of the hand-edited
  export.
- **Responsiveness:** screenshots inspected at 1440/1024/768/390/320 px for
  landing, upload, dashboard, filters, and the details panel.


**Errors the AI made, and how each was caught**

1. **The CSV round-trip bug this project was asked to fix was AI-authored.**
   The first export builder appended a summary footer — 10 fields — under a
   7-column header. Excel/LibreOffice and any strict reader then reported
   `Expected 7 fields in line 19, saw 10` on re-upload. Caught from the user's
   error report; reproduced locally, then fixed by making every export line
   exactly 10 fields with no footer, and by making the parser report offending
   row numbers instead of failing the whole file.
2. **A silently broken rule table.** `re.escape()` escapes spaces to `\ `, so
   the code that rebuilt keyword patterns produced literal-backslash regexes;
   every multi-word merchant keyword could never match. Eight failing tests
   exposed it; the fix joins pre-escaped words with `\s+`.
   *Lesson: unit tests on the matching behavior, not just "the function ran".*
3. **Truncated/invalid drafts.** Two writes produced non-compiling `brain.py`
   drafts (a `:=` placeholder and a dead `assert`). Caught immediately by the
   test run and replaced with complete files.
4. **Wrong test expectations.** Hand-computed totals for expenses and a
   currency-string sign were incorrect; the assertions were corrected after
   deriving the expected values from the documented sign convention rather
   than from whatever the code happened to output.
5. **A misdiagnosed "bug" that was correct behavior.** A round-trip test
   initially failed because an imported `Uncategorized` category was not
   preserved. That is the intended policy — the test was wrong (it patched
   only one of two flagged rows), not the code.
6. **Staged edits that produced a non-compiling file.** Two overlapping edits
   left duplicate definitions of `_parse_csv` and a mangled function boundary
   (`return records, warningsrow_values: …`). Caught by an import error, then
   repaired by deleting the stale copy and re-running the suite. *Lesson: one
   edit per coherent change, verified between edits.*
7. **A comment that asserted behavior the code did not have.** The dispute
   guard documented that a `CHARGEBACK FEE` still lands in bank fees, but no
   keyword matched it and the row fell through to Needs Review. Caught by
   writing the promised test before trusting the comment; the `bank_fees` rule
   gained `chargeback fee` / `dispute fee`.
8. **Localized aliases that collided with English.** Adding `data` (Italian:
   date) and `cargo` (Spanish: debit) as ordinary substring aliases made
   `Card data` a date column. Fixed with exact-whole-header-only aliases and
   pinned by a test that expects a `ParseError`, not a silent misread.
9. **A fixture that was wrong, not the parser.** The French sample failed to
   match `Libellé`; the file itself was malformed (header delimited with `;`,
   data row with `,`). Diagnosed by parsing the row by hand instead of
   loosening the matcher, then fixing the fixture and adding the missing alias.
10. **Landing-page numbers that did not match the product.** The hero mock's
    Income tile showed `$5,440.55` — Business Income only — while the
    dashboard's own Income KPI is `$5,444.70` (Business + Interest). Caught by
    uploading the demo file to the running API and diffing the figures; the
    mock now uses the live numbers.
11. **Delegating a date guess to a library.** Resolving `d/m/y` through
    `pandas.to_datetime(dayfirst=…)` emitted a per-value `UserWarning` when it
    had to guess, which is the same "silently picked an order" problem in a
    different place. Fixed by parsing numeric dates explicitly here and keeping
    the file-level warning as the only signal.
12. **A documented behavior the code never implemented.** The export docs
    promise a UTF-8 BOM so Excel reads `€` and `ü` correctly. Only the
    downloadable sample had one, and there it was a literal character in the
    source that a later edit silently dropped. Caught by checking the bytes of
    a file downloaded from the browser, not by any test — both exporters now
    prepend `uFEFF` as an escape.
13. **A rule that contradicted its own documentation.** `DESIGN.md` said a
    refund word on a negative amount is not guessed; the engine let the next
    merchant rule claim it and filed the row under the purchase category.
    Caught by reading the doc and the code side by side, then fixed by making
    the refund rule stop the scan, with a test for the exact case.
14. **A continental file dated the American way.** A `;`-delimited `Datum`
    file whose amounts already used decimal commas had its ambiguous
    `05/01/2026` rows read MM/DD. The number style and the date style were
    decided independently. Caught with a synthetic German fixture; date-order
    inference now takes the file's number/header style into account and says
    which reading it used.
15. **A slow path nobody timed.** `_to_date` handed every ISO date to
    `pandas.to_datetime`, which re-guesses the format per call. A statement at
    the documented 10 MB limit took 49 s to parse and was killed by the nginx
    proxy timeout with a 504 — a real failure the test suite never saw, because
    its fixtures are small. Caught only because the audit pushed a large
    synthetic file through the containerized stack; profiling pointed at one
    line, which now short-circuits ISO. Same input: 49 s → 2.8 s per 20k rows,
    and the upload returns 200 in ~20 s through nginx. Three tests pin the new
    path's error behavior (an impossible date like `2026-02-30` still raises).

Each suggestion was judged by running it: compile, execute tests, and where
behavioral, drive the UI in a browser. Claims were verified against command
output before being written down here.

**Token usage:** no exact per-session token log is retained by this project,
and none is invented here. The session was long enough to require context
compaction, i.e. substantially more than a single-window exchange; beyond that
we have no measured figure to report.

## Adding capabilities without breaking the rule

- Extend categorization coverage by adding `Rule` entries to `RULES`
  (remember: order = priority, first match wins).
- If a future feature ever needs probabilistic behavior (e.g. suggesting
  categories for flagged rows), it must live **outside** `brain.py`, be
  opt-in, and never auto-assign a category — the deterministic engine and
  the human reviewer remain the only writers of final categories.
