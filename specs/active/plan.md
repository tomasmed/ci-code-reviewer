# Technical Plan: Concise Failure Summaries & Structured CI Error Logging

* **Reference Spec**: [spec.md](./spec.md)
* **Author**: Antigravity Pair Programmer
* **Date**: 2026-10-26

---

## 1. Architectural Approach

The goal is to cleanly separate **developer-facing comment output** from **operational runner diagnostics**:

1. **Logging Layer**:
   - Use standard Python `logging.getLogger(__name__)` inside `ci_code_reviewer.harness.native` and `ci_code_reviewer.harness.maf`.
   - On lens failure, emit an error log with `exc_info=True`. This automatically prints the full exception name, message, provider JSON, and traceback to stderr/stdout in the CI runner.

2. **Presentation / Summary Layer**:
   - Instead of injecting `f"{type(e).__name__}: {e}"` into the `summary` string of `LensTurnResult`, use a standardized clean string:
     `"Sub-agent turn for lens '{lens.name}' encountered an error and could not complete review. Check CI logs for details (offline/fallback mode)."`
   - For MAF harness:
     `"MAF agent turn for lens '{lens.name}' encountered an error and could not complete review. Check CI logs for details (offline/fallback mode)."`
   - Ensure the check `if "offline/fallback mode" in summary` in both harnesses continues to accurately identify failed lenses without breaking recommendation logic or summary notes.

3. **Blast Radius Noise Reduction**:
   - Expand `IGNORE_SYMBOLS` in `src/ci_code_reviewer/context/blast_radius.py` to include:
     `"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "HANDLER", "DEFAULT"`
   - This prevents generic API route handlers from scanning hundreds of method lines across client files.

---

## 2. Affected Files & Touchpoints

### Existing Files to Modify:
* `src/ci_code_reviewer/harness/native.py`:
  - Set up module logger `logger = logging.getLogger(__name__)`.
  - Update `_execute_lens_turn` exception handling to log with `exc_info=True` and return the clean summary message.
* `src/ci_code_reviewer/harness/maf.py`:
  - Set up module logger `logger = logging.getLogger(__name__)`.
  - Update `_execute_maf_lens_turn` exception handling to log with `exc_info=True` and return the clean summary message (preserving `offline/fallback mode`).
* `src/ci_code_reviewer/context/blast_radius.py`:
  - Update `IGNORE_SYMBOLS` set with HTTP verbs and generic keywords.
* `tests/test_harnesses.py`:
  - Update tests checking for fallback summaries to verify concise messages without raw error dumps.
  - Add test asserting that logging occurs on lens failure (`caplog`).
* `tests/test_blast_radius.py`:
  - Add test asserting that HTTP verbs like `POST` and `GET` are filtered out of extracted symbols.

---

## 3. Dependencies & Libraries
* No new dependencies required. Uses Python built-in `logging`.

---

## 4. Failure Modes & Mitigations
* **Risk 1**: Harness fallback detection breaks if wording changes.
  ➔ **Mitigation**: Maintain the exact phrase `offline/fallback mode` in the concise summary message, which satisfies `if "offline/fallback mode" in summary`.
* **Risk 2**: Hidden or silent failures if someone doesn't inspect CI logs.
  ➔ **Mitigation**: The PR comment explicitly directs the user to `"Check CI logs for details"`, while the top-level summary also flags that lenses operated in fallback mode.
