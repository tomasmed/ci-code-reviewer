# Contributor Guide: Agentic SDLC & Absolute Contributor Ownership

> **The Golden Rule of Contributing to `ci-code-reviewer`**:
> AI coding agents (Cursor, Claude Code, Copilot, Antigravity, Aider) are powerful force-multipliers, and using them to craft contributions is warmly welcomed. **However, you as the human contributor own 100% of your submission.**
> If you open a pull request, you must thoroughly understand every line of code, edge case, and architectural trade-off in the diff, and you must be able to explain and defend every design decision during peer review. Blindly copying AI output or opening unchecked "vibe-coded" PRs is unacceptable.

---

## 1. Principles of Contributor Ownership

1. **You Are the Author of Record**:
   * An AI agent did not submit the pull request—**you did**.
   * "The AI wrote it" is never an acceptable explanation for buggy code, missing edge cases, hollow test assertions, or unexpected dependencies.
2. **Defend Your Code**:
   * Reviewers will ask questions about memory usage, concurrency, token consumption, and failure modes. You are expected to answer them with technical precision.
3. **Anti-Lazy-Assert Discipline**:
   * Never submit tests that merely assert `assert True`, mock out all meaningful logic, or test trivial happy paths without error cases. Every test must verify genuine business logic.
4. **Architectural Reverence**:
   * Always check `docs/adr/` and `docs/architecture/overview.md` before introducing any new abstraction, dependency, or runtime pattern.

---

## 2. The 5-Stage Contributor Workflow

```text
 ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
 │  1. INTENT    │ ──▶ │   2. DESIGN   │ ──▶ │ 3. IMPLEMENT  │
 │(Problem/Spec) │     │ (Plan & ADR)  │     │  (TDD Loop)   │
 └───────────────┘     └───────────────┘     └───────┬───────┘
                                                     │
 ┌───────────────┐     ┌───────────────┐             ▼
 │ 5. PR DEFENSE │ ◀── │  4. VERIFY    │ ◀───────────┘
 │(Human Review) │     │ (Local Gate)  │
 └───────────────┘     └───────────────┘
```

### Stage 1: Define Intent (`specs/`)
* **Objective**: Clearly frame the problem and acceptance criteria before touching code.
* For non-trivial features, draft a spec in `specs/active/spec.md` describing:
  - User story & expected behavior
  - Boundary conditions and failure scenarios
  - What is explicitly *out of scope*

### Stage 2: Plan & Architecture Alignment
* Review existing Architecture Decision Records in `docs/adr/`.
* If your change introduces a new dependency or external provider pattern, draft an ADR using `docs/adr/template.md`.
* Ensure your plan respects the core modular boundaries:
  - `harness/`: Review orchestration protocols.
  - `providers/`: Model & auth resolution.
  - `integrations/`: GitHub/CI platform APIs.

### Stage 3: Implement with Test-Driven Discipline
* Work incrementally with tests.
* Ensure unit tests cover:
  - The primary happy path.
  - Network/API failure handling and timeouts.
  - Edge cases (empty diffs, huge diffs, missing API keys, rate limits).

### Stage 4: Run the Deterministic Local Verification Gate
Before staging or pushing, run the compound verification check locally:
```powershell
# Windows PowerShell:
./.github/scripts/verify.ps1

# Linux / macOS:
./.github/scripts/verify.sh
```
* **Gate Criteria**:
  1. `ruff check .` passes with zero linter errors.
  2. `ruff format --check .` passes with zero formatting diffs.
  3. `pytest` executes all tests 100% green.
* Zero warnings or errors are permitted into Git.

### Stage 5: Peer Review & PR Defense
* Open your Pull Request with a clear summary following the PR template.
* Engage actively in the PR review discussion:
  - Explain *why* a particular approach was chosen.
  - Be receptive to feedback and iterate cleanly.
  - Once merged, celebrate your contribution!
