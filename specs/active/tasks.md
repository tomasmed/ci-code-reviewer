# Task Checklist: Concise Failure Summaries & Structured CI Error Logging

* **Reference Plan**: [plan.md](./plan.md)

> **Rules for Coding Agents**:
> 1. Execute tasks strictly in order.
> 2. Follow TDD: write/update tests before marking task as complete.
> 3. Verify each task with `./.github/scripts/verify.ps1` before checking the box (`[x]`).
> 4. Do not proceed to Task N+1 if Task N fails verification.

---

## Task Breakdown

### Phase 1: Blast Radius HTTP Verb & Noise Filtering (TDD)
- [x] **Task 1.1**: Update `tests/test_blast_radius.py` to assert that exported route handlers like `export async function POST` and `def get(...)` are ignored.
  - *Verify*: `uv run pytest tests/test_blast_radius.py` fails if HTTP verbs are extracted.
- [x] **Task 1.2**: Update `IGNORE_SYMBOLS` in `src/ci_code_reviewer/context/blast_radius.py` to ignore HTTP verbs and common keywords.
  - *Verify*: `uv run pytest tests/test_blast_radius.py` passes.

### Phase 2: Harness Error Logging & Clean Fallback Presentation (TDD)
- [x] **Task 2.1**: Update `tests/test_harnesses.py` with test verifying concise summary message without raw exception string, and asserting error logging via `caplog`.
  - *Verify*: `uv run pytest tests/test_harnesses.py` fails on old verbose error messages.
- [x] **Task 2.2**: Implement logger and concise summary formatting in `src/ci_code_reviewer/harness/native.py`.
  - *Verify*: Native harness tests in `tests/test_harnesses.py` pass.
- [x] **Task 2.3**: Implement logger and concise summary formatting in `src/ci_code_reviewer/harness/maf.py`.
  - *Verify*: MAF harness tests in `tests/test_harnesses.py` pass.

### Phase 3: Deterministic Gate Verification
- [x] **Task 3.1**: Run full verification gate (`./.github/scripts/verify.ps1`).
  - *Verify*: Ruff linter, ruff format check, and pytest suite run 100% green.
