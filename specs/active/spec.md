# Feature Specification: Concise Failure Summaries & Structured CI Error Logging in Review Harnesses

* **Status**: Approved
* **Target Release / Milestone**: v0.2.1
* **Associated Issue/PR**: Harness Resilience & Clean PR Presentation

---

## 1. Context & Business Intent

* **Problem**:
  1. When a sub-agent review lens turn fails due to upstream provider/network errors (e.g., LiteLLM `NotFoundError`, `AuthenticationError`, `RateLimitError`, or timeouts), the harness currently dumps the raw stringified exception—including multi-line JSON error bodies and provider URLs—directly into the lens turn summary.
  2. Because the lens summary is rendered in both the "Review Lens Evaluations" section and the "QA & Test Integrity" section (for `test_integrity`), the exact same raw error JSON is repeated multiple times across the PR comment.
  3. This creates excessive noise, degrades developer experience, risks leaking internal provider URLs or API metadata, and pollutes PR discussion threads.
  4. Furthermore, because errors were not logged to standard logging streams with stack traces, developers inspecting CI execution logs lacked structured debugging context in runner output.
  5. As a related noise issue, `blast_radius.extract_modified_symbols` matches standard HTTP verbs (e.g. `POST`, `GET`) exported in route handlers (e.g., Next.js `export async function POST`), causing blast radius to scan and dump dozens of common method references across unrelated frontend files.

* **User Story**:
  As a developer receiving automated code reviews, I want failure notifications in PR comments to be concise, clean, and actionable, with full diagnostic stack traces routed to CI runner logs, so that PR reviews remain focused and uncluttered while retaining complete observability in CI.

---

## 2. Functional Requirements

1. **Structured CI Error Logging**:
   - `NativeReviewHarness` and `MafReviewHarness` must log review lens exceptions using standard Python `logging` (`logger.error(...)` with `exc_info=True`).
   - CI runner logs (GitHub Actions stdout/stderr) will capture the full provider error, exception class, and traceback for troubleshooting.

2. **Concise User-Facing Failure Summary**:
   - In `NativeReviewHarness._execute_lens_turn`, replace raw stringified exceptions with a concise, developer-friendly message:
     `Sub-agent turn for lens '{lens.name}' encountered an error and could not complete review. Check CI logs for details (offline/fallback mode).`
   - In `MafReviewHarness._execute_maf_lens_turn`, replace raw stringified exceptions with:
     `MAF agent turn for lens '{lens.name}' encountered an error and could not complete review. Check CI logs for details (offline/fallback mode).`
   - The phrase `offline/fallback mode` must be preserved in the summary to guarantee uninterrupted operation of fallback stance detection (`all_lenses_fell_back`).

3. **Blast Radius Keyword Filtering**:
   - Add standard HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`) and common noise keywords to `IGNORE_SYMBOLS` in `src/ci_code_reviewer/context/blast_radius.py` to prevent route handlers from polluting the downstream blast radius analysis.

---

## 3. Boundary Conditions & Edge Cases

* **All Lenses Fail**: When all active review lenses fail (e.g. invalid API key or model unavailable), top-level assessment summary continues to clearly indicate open-stance fallback mode, and each lens summary remains concise without repeating stack traces.
* **Partial Lens Failure**: If one lens encounters an error while others succeed, the successful lenses report their findings and the failing lens reports the concise fallback message with fallback count noted in top-level summary.
* **Empty/Missing Error Strings**: Handled gracefully without `None` formatting or missing details.
* **Logging Capture**: Logging must not raise exceptions even if logger handlers are not explicitly configured by caller.

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] Lens turn exceptions are logged with `logger.error(..., exc_info=True)`.
- [ ] PR summaries contain concise, non-spammy messages referencing CI logs and maintaining `offline/fallback mode`.
- [ ] No raw JSON error dumps, URLs, or tracebacks appear in `ReviewAssessment` summaries.
- [ ] Common HTTP methods (`POST`, `GET`, etc.) are ignored during blast radius symbol extraction.
- [ ] Unit tests in `tests/test_harnesses.py` and `tests/test_blast_radius.py` verify clean summaries and keyword exclusion.
- [ ] `./.github/scripts/verify.ps1` runs 100% green with zero errors or warnings.
