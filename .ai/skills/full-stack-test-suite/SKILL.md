---
name: "full-stack-test-suite"
description: "Detect a repository's backend language and run its native test framework (pytest, cargo test, go test, mvn/gradle, npm test, dotnet test, rspec, phpunit); detect and run frontend browser end-to-end tests (Playwright/Selenium/Cypress) only when they already exist in the repo; query historical Playwright CI results from the aggregated DuckDB database (flaky tests, failure rates, slow tests); and generate new backend + frontend test cases from PRD/HLD/LLD requirement documents (not from code diffs), execute them, and produce a DOCX review report."
user_invocable: true
---

# Full-Stack Test Suite

This skill has four parts. Parts A and B decide *how to run what already
exists* in the repo. Part C lets you query historical CI signal. Part D
generates and runs *new* tests, driven by requirements documents rather than
by reading the implementation.

**Never assume every repository uses Playwright.** Playwright/Selenium/Cypress
only apply when the repo actually contains browser-based end-to-end tests;
otherwise, always prefer the repo's native backend test framework.

---

## Part A — Detect and run native backend tests

### Step A1: Detect repository type

Inspect the repository root for build files:

| Repository Type | Detection Files | Test Framework | Command |
|-----------------|-----------------|---------------|---------|
| Python | `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `Pipfile`, `poetry.lock` | pytest | `pytest` |
| Java (Maven) | `pom.xml` | JUnit/TestNG | `mvn test` |
| Java (Gradle) | `build.gradle`, `build.gradle.kts`, `gradlew` | JUnit/TestNG | `./gradlew test` |
| Rust | `Cargo.toml` | cargo test | `cargo test` |
| Go | `go.mod` | go test | `go test ./...` |
| Node.js | `package.json` | Jest/Vitest/Mocha | `npm test` |
| .NET | `*.csproj`, `*.sln` | dotnet test | `dotnet test` |
| Ruby | `Gemfile` | RSpec | `bundle exec rspec` |
| PHP | `composer.json` | PHPUnit | `vendor/bin/phpunit` |

### Step A2: Determine the primary language

If multiple languages exist:
1. Prefer the language tied to the repo's primary build file.
2. Ignore example/demo folders unless they're the main project.
3. If the repo contains multiple independent projects, test each independently.

### Step A3: Execute native tests

Run the command from the table above for the detected language, e.g.
`pytest`, `cargo test`, `go test ./...`, `mvn test`, `./gradlew test`,
`npm test`, `dotnet test`.

### Step A4: Collect results

Summarize: tests executed, passed, failed, skipped, stack traces, compilation
errors, build failures. Provide actionable suggestions for fixing failures.

---

## Part B — Detect and run frontend browser tests

### Step B1: Detect browser tests

Only after native tests complete, check for browser automation config:

```
playwright.config.ts / .js / .py / .java
cypress.config.*
tests/e2e/
e2e/
selenium/
```

### Step B2: Run browser automation

- If Playwright config exists: run the existing Playwright tests; analyze
  traces, screenshots, videos, and failures.
- If Selenium suites exist: execute them via the repo's existing test runner.
- If Cypress config exists: run via `cypress run`.

**Do not create new browser tests here** — that only happens in Part D, and
only when the requirements docs call for it. This part only runs what's
already there.

### Decision matrix

| Repository | Action |
|------------|--------|
| Python SDK | Run pytest |
| Rust crate | Run cargo test |
| Java library | Run Maven/Gradle tests |
| Go library | Run go test |
| Node library | Run npm test |
| React frontend | Run Playwright if configured |
| Spring Boot backend | Run JUnit tests |
| Spring Boot + React | Run backend tests first, then Playwright if configured |

---

## Part C — Query historical Playwright CI results (DuckDB)

A DuckDB file holds recent Playwright CI test results (refreshed every few
hours), useful for prioritizing *where* new tests matter most in Part D.

### Get the database

```bash
npm ci                       # first time only, from the repo root
GITHUB_TOKEN=$(gh auth token) node utils/test-results-db/cli.ts download
GITHUB_TOKEN=$(gh auth token) node utils/test-results-db/cli.ts update --lookback-days 3
```

Query via the bundled `@duckdb/node-api` binding (no separate DuckDB install):

```bash
node --input-type=module -e '
import { DuckDBInstance } from "@duckdb/node-api";
const conn = await (await DuckDBInstance.create("utils/test-results-db/test-results.duckdb")).connect();
console.table((await conn.runAndReadAll(process.argv[1])).getRowObjectsJson());
' "SELECT count(*) FROM test_results"
```

Integer columns come back as strings (JSON-safe) — rank/filter in SQL, not JS.

### Schema

One row per test result (**per retry**), inferred from the reporter's parquet
(`tests/config/parquetReporter.ts`), plus two columns this CLI adds:

| Column | Meaning |
| --- | --- |
| `run_id`, `run_attempt` | GitHub Actions run identity |
| `run_started_at` | when the run started |
| `workflow_name` | e.g. `tests 1` / `tests 2` / `tests others` / `MCP` |
| `event` | `push` / `pull_request` |
| `head_sha`, `head_branch`, `pr_number` | what was tested |
| `bot_name` | CI bot, e.g. `chromium-ubuntu-22.04-node20` — **OS/arch encoded here**, no separate os column |
| `project_name` | CI project = browser + suite, e.g. `chromium-page`, `webkit-library` |
| `test_title` | title path, joined by ` › ` (`describe › test`) |
| `file`, `line`, `column_number` | source location (relative to repo root) |
| `expected_status` | `passed` / `skipped` / ... |
| `status` | actual result: `passed` / `failed` / `timedOut` / `skipped` / `interrupted` |
| `retry` | 0 = first attempt |
| `result_started_at` | when this attempt started |
| `duration_ms` | result duration |
| `error_message` | all errors joined, ANSI-stripped (NULL when none) |
| `tags` | **list** of strings, e.g. `['@slow', '@flaky']` |
| `annotations` | list of `{type, description}` structs |
| `artifact_id` | source GitHub artifact (dedupe key) |
| `ingested_at` | debug only |

Notes:
- **A test is identified by `(project_name, file, test_title)`.**
- **Flakiness is derived, not stored.** Cross-run flake = final verdict flips
  between separate runs. Within-run flake = a retry rescued a failure inside
  one run (`failed`→`passed`).
- Filter `expected_status = 'passed'` to exclude intentional `test.fail()` tests.
- The DB is size-capped by run count — a recent window, not full history.

### Example queries

**Flaky across runs** (`least(failed_runs, passed_runs)` ranks genuinely
bimodal tests above always-broken or one-off failures):

```sql
WITH per_run AS (
  SELECT project_name, file, test_title, run_id, run_attempt,
         arg_max(status, retry) AS final_status,
         any_value(expected_status) AS expected
  FROM test_results
  GROUP BY project_name, file, test_title, run_id, run_attempt)
SELECT project_name, test_title,
       count(*) AS runs,
       count(*) FILTER (WHERE final_status IN ('failed','timedOut')) AS failed_runs,
       count(*) FILTER (WHERE final_status = 'passed') AS passed_runs,
       round(100.0 * count(*) FILTER (WHERE final_status IN ('failed','timedOut'))
             / count(*), 1) AS fail_pct
FROM per_run
WHERE expected = 'passed'
GROUP BY project_name, test_title
HAVING failed_runs > 0 AND passed_runs > 0 AND runs >= 10
ORDER BY least(failed_runs, passed_runs) DESC, failed_runs DESC
LIMIT 20;
```

**Filter by tag** (`tags` is a list, not a string):

```sql
SELECT project_name, test_title, count(*) AS runs
FROM test_results
WHERE list_contains(tags, '@slow')
GROUP BY project_name, test_title
ORDER BY runs DESC
LIMIT 20;
```

### Linked emoji run history

Renders a test's run history as clickable emoji squares (🟩 pass, 🟧
retry-rescued, 🟥 fail) for a GitHub comment. Edit the four identity fields,
then run:

```bash
node --input-type=module <<'EOF'
import { DuckDBInstance } from "@duckdb/node-api";

const repository = "microsoft/playwright";
const test = {
  projectName: "firefox-library",
  file: "library/proxy.spec.ts",
  testTitle: "should exclude patterns",
  botName: "firefox-macos-15-large",
};

const conn = await (await DuckDBInstance.create(
  "utils/test-results-db/test-results.duckdb"
)).connect();
const result = await conn.runAndReadAll(`
  WITH per_run AS (
    SELECT run_id, run_attempt,
           any_value(run_started_at) AS run_started_at,
           arg_max(status, retry) AS final_status,
           arg_max(expected_status, retry) AS expected_status,
           list(status ORDER BY retry) AS attempt_statuses
    FROM test_results
    WHERE project_name = $projectName
      AND file = $file
      AND test_title = $testTitle
      AND bot_name = $botName
    GROUP BY run_id, run_attempt
  )
  SELECT run_id, run_attempt, final_status, attempt_statuses
  FROM per_run
  WHERE expected_status = 'passed'
    AND final_status IN ('passed', 'failed', 'timedOut')
  ORDER BY run_started_at, run_id, run_attempt
`, test);

const markdown = result.getRowObjectsJson().map(row => {
  const rescued = row.final_status === "passed" &&
    row.attempt_statuses.some(status => status === "failed" || status === "timedOut");
  const emoji = rescued ? "🟧" : row.final_status === "passed" ? "🟩" : "🟥";
  const url = `https://github.com/${repository}/actions/runs/${row.run_id}/attempts/${row.run_attempt}`;
  return `[${emoji}](${url})`;
}).join("");

console.log(markdown);
EOF
```

Output: `[🟩](...)[🟧](...)[🟥](...)` — one square per run attempt, oldest
first. `arg_max(status, retry)` picks the final verdict after retries;
grouping by `(run_id, run_attempt)` keeps retries from becoming extra squares.

### Fetching full detail

The DB stores summaries only. For the full step tree / attachments / stdio,
fetch the run's blob report artifact (named `blob-report-<bot_name>`):

```bash
gh api /repos/microsoft/playwright/actions/runs/<run_id>/artifacts \
  --jq '.artifacts[] | select(.name | startswith("blob-report")) | {id, name}'
gh api /repos/microsoft/playwright/actions/artifacts/<artifact_id>/zip > blob.zip
```

---

## Part D — Generate test cases from PRD / HLD / LLD, run them, and report

### Why requirements-driven, not code-driven

Generation here is deliberately based on the **PRD (Product Requirements
Document), HLD (High-Level Design), and LLD (Low-Level Design)** — not on
reading the implementation or diffing commits. Code reflects what was *built*;
it can silently encode the same bugs or gaps the tests are meant to catch, and
a diff only shows what changed, not what the system was actually supposed to
do. Requirements documents state *intended* behavior independently of the
implementation, so tests generated from them can catch cases where the code
diverges from intent — including missing functionality that never produced a
diff at all. Historical CI data (Part C) is still used, but only to
*prioritize* which requirement areas to cover first, never as a substitute for
the requirements themselves.

### Step D1: Locate and read the requirement documents

Find the PRD, HLD, and LLD for the feature/system under test — typically in a
`docs/`, `design/`, or `requirements/` folder, a linked wiki/Confluence page,
or attached directly. Read all three where available:
- **PRD** — what the feature must do, for whom, and why (user stories,
  acceptance criteria, business rules).
- **HLD** — system-level design: components, services, data flow, integration
  points, major interfaces.
- **LLD** — implementation-level design: specific APIs/endpoints, request/
  response schemas, function signatures, database schema, state machines,
  error-handling contracts.

If a document is missing, proceed with what's available and record the gap in
the final report rather than falling back to reading the code.

### Step D2: Extract testable requirements

From the PRD, pull out discrete, testable statements: acceptance criteria,
user flows, business rules, non-functional requirements (performance,
security, accessibility). From the HLD, pull out component boundaries and
integration contracts to test at. From the LLD, pull out concrete, checkable
specifics: endpoint signatures, input/output schemas, validation rules,
status/error codes, state transitions, data constraints. Assign each a short
requirement ID (e.g. `PRD-3.2`, `LLD-API-Login-4`) for traceability.

### Step D3: Route each requirement to a test layer

Using the detection from Parts A and B, decide where each requirement should
be tested:
- Requirements about a UI flow, page, or user-visible behavior → frontend
  browser test (Playwright/Selenium/Cypress — whichever this repo already
  uses, per Part B).
- Requirements about an API, service logic, data layer, or business rule →
  backend native test framework (per Part A's detected framework).
- Requirements spanning both → cover at both layers with a shared requirement
  ID linking them.

### Step D4: Generate the test cases

For each requirement, write a test in the appropriate framework/language and
project convention (existing fixtures, helpers, `describe`/`test.describe`
structure, naming, assertion style). Cover, as relevant to the requirement:
happy path, boundary conditions, invalid/empty/null/min/max input,
authorization/authentication/permission rules, error handling and messaging,
state transitions defined in the LLD, and non-functional requirements called
out in the PRD. Do not invent behavior the documents don't describe, and do
not rewrite existing tests unless expanding them improves coverage of a
requirement.

### Step D5: Record traceability

For every generated test, note: the requirement ID(s) it validates, which
document (PRD/HLD/LLD) it came from, and — if applicable — which historical CI
signal from Part C influenced its priority.

### Step D6: Execute the generated tests

Run each generated test through its native framework/command from Part A, or
through the detected browser framework from Part B, e.g.:

```bash
# Backend, e.g. Python
pytest <generated_test_file> --junitxml=/tmp/generated-backend.xml

# Frontend, e.g. Playwright
npx playwright test <generated-spec-file> --reporter=json > /tmp/generated-frontend.json
```

Capture pass/fail, duration, error messages, stack traces, and any
screenshots/videos/traces produced.

### Step D7: Analyze the results

For each generated test, determine passed / failed / timed out / flaky /
skipped. For failures, determine whether it indicates a genuine deviation from
the requirement (a real bug), a wrong assumption in the generated test, missing
test setup, an environment issue, or an ambiguity in the requirement doc
itself worth flagging back to the author — don't default to assuming the
application is wrong.

### Step D8: Produce the DOCX review report

Build a Word document (see the `docx` skill for creation mechanics — page
size, tables, TOC, etc.) containing:

1. Requirement documents used (PRD/HLD/LLD) and any that were missing.
2. Extracted requirements and their IDs.
3. Requirement → test-layer routing (backend vs. frontend).
4. Newly generated tests, grouped by requirement ID.
5. Traceability: requirement ↔ test ↔ (optional) historical CI evidence.
6. Native backend test results (Part A).
7. **Page break**, then browser/frontend test results (Part B).
8. Generated test execution results (Step D6–D7).
9. Newly discovered deviations from the requirements (bugs).
10. Requirements with no corresponding test (coverage gaps).
11. Recommendations for additional manual/exploratory testing.

Insert an explicit page break between the backend review (item 6) and the
frontend review (item 7) so each starts on its own page — they're distinct
audiences (backend vs. frontend engineers) and different result shapes. With
`docx` (via the `docx` skill), a page break is a `PageBreak` element placed
inside its own `Paragraph`, immediately after the backend section and before
the frontend section's heading:

```javascript
new Paragraph({ children: [new PageBreak()] }),
new Paragraph({ text: "Frontend Test Results", heading: HeadingLevel.HEADING_1 }),
```

Save to `~/Desktop/Reviews/`, creating the folder if needed:

```bash
mkdir -p ~/Desktop/Reviews
# ... after building output.docx via the docx skill ...
cp output.docx ~/Desktop/Reviews/<date>-<feature>-test-review.docx
```

`~/Desktop/Reviews` is a path on the local machine running this skill —
confirm it exists and is writable before assuming the report landed there,
and adjust the path if the environment doesn't have a conventional Desktop
folder (e.g. headless CI runners).

---

## Rules

- Never assume Playwright (or any browser framework) is required — always
  detect first.
- Always prefer the repository's native backend test framework for existing
  backend tests (Part A).
- Only run browser automation when browser tests already exist (Part B); only
  create *new* browser tests in Part D, and only from requirements docs.
- Generate new test cases from PRD/HLD/LLD requirements — not from reading or
  diffing the implementation code.
- Use historical CI data (Part C) to prioritize, never as the sole or primary
  source of new tests.
- If no native tests are found, explain why and recommend an appropriate
  framework for the detected language rather than silently skipping.
- Report backend, frontend, and generated-test results separately and clearly.

## Expected output

1. Detected backend language and build system (Part A).
2. Native test framework, command, and results (Part A).
3. Browser test detection result and results, if any (Part B).
4. Requirement documents consulted and extracted requirement list (Part D).
5. Generated tests with requirement traceability (Part D).
6. Generated-test execution results and any newly found deviations (Part D).
7. Path to the DOCX review report.
8. Final recommendations (coverage gaps, manual testing follow-ups).
