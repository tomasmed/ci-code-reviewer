# Task Checklist: GitHub PR Ingestion, Publishing, & Workspace Blast Radius (with MAF Multi-Lens Support)

* **Reference Plan**: [plan.md](./plan.md)

> **Rules for Coding Agents**:
> 1. Execute tasks strictly in order.
> 2. Follow TDD: write/update tests before marking task as complete.
> 3. Verify each task with `bash ./.github/scripts/verify.sh` before checking the box (`[x]`).
> 4. Do not proceed to Task N+1 if Task N fails verification.

---

## Task Breakdown

### Phase 1: Workspace Context & Downstream Blast Radius Scanner (TDD)
- [x] **Task 1.1**: Create `tests/test_blast_radius.py` to test symbol extraction and downstream caller reference scanning across workspace files.
  - *Verify*: `uv run pytest tests/test_blast_radius.py` fails (module not implemented).
- [x] **Task 1.2**: Implement `src/ci_code_reviewer/context/blast_radius.py` (`extract_modified_symbols`, `find_downstream_references`, `format_blast_radius_context`).
  - *Verify*: `uv run pytest tests/test_blast_radius.py` passes.

### Phase 2: GitHub Integration Client & Voting Policy (TDD)
- [x] **Task 2.1**: Update `src/ci_code_reviewer/config.py` with `VotingConfig` (`enabled`, `allow_approve`, `allow_request_changes`).
  - *Verify*: `uv run pytest tests/test_config.py` or existing tests pass.
- [x] **Task 2.2**: Create `tests/test_github_integration.py` testing `GitHubClient` (diff fetching, PR info extraction, review formatting, voting event resolution, and 422 fallback resilience).
  - *Verify*: `uv run pytest tests/test_github_integration.py` fails (module not implemented).
- [x] **Task 2.3**: Implement `src/ci_code_reviewer/integrations/github.py` with `GitHubClient` using `httpx`.
  - *Verify*: `uv run pytest tests/test_github_integration.py` passes.

### Phase 3: Microsoft Agent Framework (MAF) Multi-Lens Alignment
- [x] **Task 3.1**: Update `tests/test_harnesses.py` to test MAF multi-lens turn orchestration, summary generation, and blast radius handling.
  - *Verify*: Tests run and verify MAF contract.
- [x] **Task 3.2**: Implement multi-lens orchestration and blast radius context in `src/ci_code_reviewer/harness/maf.py`.
  - *Verify*: `uv run pytest tests/test_harnesses.py` passes.

### Phase 4: CLI Wiring & Action Integration (TDD)
- [x] **Task 4.1**: Create `tests/test_cli.py` testing `ci-code-reviewer review` with `--diff-file`, `--pr`, `--dry-run`, blast radius injection, and exit codes.
  - *Verify*: Tests run and fail on stub CLI implementation.
- [x] **Task 4.2**: Wire CLI logic in `src/ci_code_reviewer/cli.py` to perform hybrid diff retrieval, blast radius scan, harness execution, console rendering, and GitHub review posting.
  - *Verify*: `uv run pytest tests/test_cli.py` passes.
- [x] **Task 4.3**: Update `action.yml` to supply `GITHUB_REPOSITORY: ${{ github.repository }}`.
  - *Verify*: Valid YAML and correct parameter pass-through.

### Phase 5: Deterministic Gate Verification
- [x] **Task 5.1**: Run full verification suite (`bash ./.github/scripts/verify.sh`).
  - *Verify*: Ruff lint, ruff format check, and all pytests are 100% green.
