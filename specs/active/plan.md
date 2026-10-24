# Technical Plan: GitHub PR Ingestion, Publishing, & Workspace Blast Radius (with MAF Multi-Lens Support)

* **Reference Spec**: [spec.md](./spec.md)
* **Author**: Antigravity Pair Programmer
* **Date**: 2026-10-24

---

## 1. Architectural Approach

The system connects four modular layers, maximizing the advantage of running directly on the CI runner with full access to the cloned repository:

```
                  ┌────────────────────────────────────────┐
                  │              CLI Ingestion             │
                  │ - Read flags: --pr, --diff-file, etc.  │
                  │ - Resolve GITHUB_TOKEN & REPOSITORY    │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │    Local Git / GitHub Hybrid Ingest    │
                  │ - Try local git diff (origin/<base>)   │
                  │ - Fallback: GitHub REST API diff       │
                  │ - Extract head commit SHA & PR info    │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │   Workspace & Blast Radius Scanner     │
                  │ - Detect altered symbols in diff       │
                  │ - Scan local workspace for callers     │
                  │ - Aggregate ADRs & in-repo lenses      │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       Review Harness Abstraction       │
                  │ - NativeReviewHarness                  │
                  │ - MafReviewHarness (MAF)               │
                  │ - StrandsReviewHarness                 │
                  │   -> Evaluates active review lenses    │
                  │   -> Consumes diff + blast context     │
                  │   -> Produces ReviewAssessment         │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │   Smart GitHub Publisher / Dry-Run     │
                  │ - Anchor inline comments on diff lines │
                  │ - Route out-of-hunk breakages to body  │
                  │ - POST /repos/{repo}/pulls/{pr}/reviews│
                  └────────────────────────────────────────┘
```

### Module Responsibilities:

1. **`ci_code_reviewer.context.blast_radius`**:
   - `extract_modified_symbols(diff: str) -> list[str]`: Scans added/modified/removed lines for function, method, and class signatures (`def foo`, `class Bar`, `function baz`, `export const qux`).
   - `find_downstream_references(symbols: list[str], workspace_root: Path, ignore_patterns: list[str]) -> dict[str, list[str]]`: Scans unchanged files in the workspace for calls and imports of those symbols.
   - `format_blast_radius_context(references: dict[str, list[str]]) -> str`: Formats discovered callers into clean markdown context to feed into sub-agent turns.

2. **`ci_code_reviewer.integrations.github`**:
   - `GitHubClient`:
     - `get_pr_diff(repo: str, pr_number: int) -> str`
     - `get_pr_info(repo: str, pr_number: int) -> dict` (head SHA, base ref)
     - `post_review(repo: str, pr_number: int, commit_id: str, assessment: ReviewAssessment) -> dict`
   - Validates diff hunk lines to prevent HTTP 422 errors. If an inline comment line is outside the PR diff hunks, it is automatically appended to the top-level review body under a **"Downstream Impact & Out-of-Diff Observations"** section.

3. **`ci_code_reviewer.harness.maf` (Microsoft Agent Framework)**:
   - Evaluates each active review lens as a specialized agent turn.
   - Passes the diff, in-repo ADRs/lenses, and blast radius context.
   - Produces standard `ReviewAssessment`.

4. **`ci_code_reviewer.cli`**:
   - Orchestrates the pipeline: resolves repo & token, obtains diff, scans blast radius, invokes harness, and publishes or dry-run prints.

---

## 2. Affected Files & Touchpoints

### New Files to Create:
* `src/ci_code_reviewer/context/__init__.py` - Context package export.
* `src/ci_code_reviewer/context/blast_radius.py` - Symbol extraction and downstream caller reference scanner.
* `src/ci_code_reviewer/integrations/__init__.py` - Integrations package export.
* `src/ci_code_reviewer/integrations/github.py` - GitHub REST API client with diff retrieval, metadata parsing, and smart review posting.
* `tests/test_blast_radius.py` - Unit tests for symbol extraction and reference scanning.
* `tests/test_github_integration.py` - Unit tests for GitHub API client and 422 recovery.
* `tests/test_cli.py` - CLI end-to-end tests for `--pr`, `--diff-file`, `--dry-run`, and blast radius injection.

### Existing Files to Modify:
* `src/ci_code_reviewer/harness/native.py` - Incorporate blast radius context into lens prompt generation.
* `src/ci_code_reviewer/harness/maf.py` - Implement multi-lens orchestration and blast radius awareness for MAF.
* `src/ci_code_reviewer/cli.py` - Wire end-to-end review command.
* `action.yml` - Add `GITHUB_REPOSITORY: ${{ github.repository }}` to step environment.

---

## 3. Dependencies & Libraries
* No new dependencies. Uses existing `httpx`, `pydantic`, `typer`, `rich`, `litellm`.

---

## 4. Failure Modes & Mitigations

* **Risk 1: Grep / Search Performance on Huge Monorepos**:
  * *Mitigation*: Limit symbol reference scanning to first 20 modified symbols and skip ignored patterns (`.git`, `node_modules`, lock files, `dist`, `build`). Limit search output to max 10 references per symbol.
* **Risk 2: GitHub 422 Unprocessable Entity**:
  * *Mitigation*: Inline comments are checked against known touched files/lines. Any failed comment is merged into the top-level review body.
* **Risk 3: Detached Git in CI**:
  * *Mitigation*: Try local `git diff`, but gracefully fall back to GitHub REST API diff if git command fails.
