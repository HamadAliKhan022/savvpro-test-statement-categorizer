# AI Usage Policy — StatementIQ

## 1. Core Requirement: Deterministic Transaction Categorization

StatementIQ is designed to categorize financial transactions using a deterministic, explainable, and auditable rule-based engine.

**No external LLMs or AI models (including GPT, Claude, Gemini, or similar models) are used to make transaction categorization decisions at runtime.** The categorization engine operates independently of generative AI and machine-learning services.

Every automatic classification is produced by `backend/app/engine/brain.py`, a Python module that evaluates an ordered set of regular-expression and keyword rules. Transactions that cannot be confidently classified are marked `Needs Review` rather than assigned speculative categories.

This restriction is a core product requirement, not simply a technical preference.

## 2. How the AI Restriction Is Enforced

The project enforces this requirement through the following mechanisms:

1. **Isolated categorization engine:** The `categorize(description, amount)` function returns a decision using deterministic rules without making network requests or calling external models.

2. **Automated testing:** The `TestNoLLMConstraint` test in `backend/tests/test_brain.py` examines the engine's syntax tree and checks for imports from known AI and machine-learning libraries.

3. **Fail-safe classification:** Unrecognized or ambiguous transactions are sent for human review instead of being assigned categories based on probabilistic predictions.

4. **Transparent API and interface:** The `/api/health` endpoint identifies the engine as `deterministic-rule-engine-v1` and reports `llm_used: false`. The interface also displays a `Rule engine only · No LLMs` indicator.

Merchant names that happen to contain words such as `openai` or `anthropic` are treated as ordinary transaction-description keywords. Matching these names does not involve calling an AI model.

## 3. AI Tool Used and Division of Work

**AI tool used:** ChatGPT by OpenAI.

ChatGPT was used as a development assistant during the implementation of StatementIQ. Its role was to help with technical planning, code suggestions, debugging, documentation, and reviewing potential edge cases.

The overall development process was approximately **50% AI-assisted and 50% my own work**. This is a qualitative estimate of the contribution, not a measured percentage of lines of code or development time.

### Work Assisted by ChatGPT

ChatGPT helped me with:

- Planning the application architecture and organizing the FastAPI backend and React/Vite frontend.
- Suggesting implementations for CSV and JSON parsing, transaction normalization, and merchant categorization rules.
- Identifying potential edge cases involving refunds, transfers, duplicate transactions, ambiguous descriptions, and malformed statements.
- Improving the user interface, including the landing page, dashboard, summary cards, category totals, filtering, pagination, and transaction details.
- Reviewing responsive layouts and suggesting improvements for smaller screens.
- Developing and refining automated test cases.
- Improving project documentation, including `README.md`, `DESIGN.md`, and this AI usage disclosure.
- Reviewing deployment configuration and discussing Docker, Nginx, and CI setup.
- Investigating bugs and suggesting fixes based on error messages, test results, and observed application behavior.

### My Own Work and Responsibilities

I remained actively involved in the development process and was responsible for directing and validating the implementation.

My contributions included:

- Defining the project requirements and the freelance-designer use case.
- Making architectural and implementation decisions based on the assignment requirements.
- Integrating AI-assisted suggestions into the actual project and adapting them to the existing codebase.
- Reviewing the categorization rules and ensuring that uncertain transactions would not be automatically guessed.
- Running the application locally and investigating errors encountered during development.
- Evaluating parser behavior with different CSV formats, including localized headers, delimiters, date formats, and currency representations.
- Running automated tests and using the results to identify incorrect implementations and test assumptions.
- Verifying transaction totals, category changes, refund handling, duplicate detection, and export/re-import behavior.
- Checking the application in a real browser and evaluating its responsive behavior at desktop, tablet, and mobile viewport widths.
- Reviewing generated code and documentation, correcting inaccuracies, and ensuring that documented behavior matched the implementation.
- Performing final validation of the backend, frontend build, and containerized application.

I did not accept every AI suggestion without checking it. When the implementation produced errors or contradicted the requirements, I investigated the problem, used test results or direct observations to identify the cause, and revised the implementation accordingly.

The 50/50 division represents my estimate of the overall contribution of AI assistance and my own work. It should not be interpreted as a precise measurement of code authorship.

## 4. AI Was Not Used for Runtime Categorization

Although ChatGPT assisted during development, it is not part of the transaction-processing workflow.

Specifically, ChatGPT was not used by the running application for:

- Classifying uploaded transactions.
- Generating transaction embeddings.
- Training a machine-learning categorization model.
- Making external model requests during transaction processing.
- Automatically assigning categories to transactions requiring human review.

The application uses deterministic rules for automatic categorization and requires human intervention when those rules cannot confidently resolve a transaction.

## 5. Testing and Verification

The implementation was evaluated through automated tests, production builds, API checks, browser-based workflows, and export/re-import testing.

The final local audit reported:

- **133 passing backend tests** using pytest.
- A successful frontend production build using `npm run build`.
- Successful API behavior checks against both the development server and the Nginx-proxied application.
- Verification of CSV parsing behavior involving quoted commas, escaped quotes, embedded newlines, delimiters, localized headers, and malformed rows.
- Checks for refunds, transfers, duplicate detection, ambiguous dates, and transaction sign conventions.
- Browser-based verification of uploading statements, reviewing transactions, editing categories, updating dashboard totals, and exporting and re-importing files.
- Responsive layout checks at viewport widths of 1440, 1024, 768, 390, and 320 pixels.
- Verification of the containerized application and its upload workflow.

These results represent the reported local verification. They do not imply that GitHub Actions CI has been observed running successfully.

## 6. Development Issues and Lessons Learned

AI-assisted development was useful, but it also produced errors that required investigation and correction. Several examples illustrate why I combined AI assistance with independent testing and verification.

1. **CSV export incompatibility:** An earlier export implementation appended a summary footer with a different number of fields from the header. This caused strict CSV readers to reject the file. The issue was reproduced and corrected by making the exported structure consistent and improving malformed-row reporting.

2. **Incorrect keyword matching:** An implementation using `re.escape()` generated patterns that failed to match some multi-word merchant names. Tests exposed the problem, and the pattern construction was corrected.

3. **Invalid code drafts:** Some intermediate edits produced incomplete or non-compiling Python code. Compilation and test runs exposed the errors before the implementation was accepted.

4. **Incorrect test expectations:** Some expected financial totals and currency-sign interpretations were wrong. The expected values were recalculated using the documented transaction sign conventions rather than simply accepting the implementation's output.

5. **Refund classification:** A refund-related description with a negative amount could fall through to a merchant rule and receive an inappropriate purchase category. The rule engine was updated to flag this ambiguous case for review.

6. **Localized date interpretation:** Some European-style statement formats could be interpreted using American date conventions. Additional file-level inference and tests were introduced to make date interpretation more consistent and transparent.

7. **CSV encoding:** The browser export did not initially include the UTF-8 byte-order mark promised by the documentation. The downloaded file was checked directly, and the export implementation was corrected.

8. **Large-file performance:** Testing a large synthetic statement exposed a slow date-parsing path that could cause a proxy timeout. The ISO-date parsing path was optimized and then measured again.

These issues reinforced several important lessons: AI-generated code must be reviewed, expected behavior should be tested explicitly, financial calculations should be independently checked, and performance should be measured rather than assumed.

## 7. Transparency About Token Usage

No reliable per-session token log was retained for this project. Therefore, I have not invented an exact token count or claimed a measured AI-to-human contribution ratio.

The estimated 50/50 division describes my overall assessment of AI assistance versus my own development, decision-making, integration, testing, debugging, and verification work.

## 8. Extending the Project Safely

Future categorization improvements should normally be implemented by adding or refining deterministic rules in the engine's `RULES` table. Rule order determines priority, with the first matching rule taking precedence.

If a future feature introduces AI-based suggestions, it must remain separate from the deterministic categorization engine, be explicitly optional, and never automatically overwrite final transaction categories.

The rule-based engine and human reviewer must remain responsible for final categorization decisions.

## 9. Conclusion

ChatGPT assisted me throughout the development of StatementIQ, particularly with technical planning, implementation suggestions, debugging, interface improvements, documentation, and test design. I contributed by defining the requirements, directing the work, integrating and reviewing code, investigating errors, testing actual behavior, and validating the final application.

I estimate the overall contribution as approximately **50% AI assistance and 50% my own work**. This estimate is not a precise measurement, but it reflects the collaborative development process I followed.

Most importantly, AI was used as a development aid, not as the transaction-categorization mechanism. StatementIQ's runtime categorization remains deterministic, explainable, and designed to send uncertain cases to human review.
