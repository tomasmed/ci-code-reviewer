# AGENTS.md — Universal Agent Operating Contract & Repository Guide

> **Note to Agents**: This repository is the Single Source of Truth (SSOT) for instructions. Adhere strictly to the commands, constraints, and workflows outlined below.

---

## 1. Project Status & Technology Stack

* **State**: `INITIALIZED`
* **Project**: CI Code Reviewer (`ci-code-reviewer`)
* **Description**: Open-source agentic code reviewer designed to run as a GitHub Action and CI/CD pipeline step.
* **Ecosystem**: Python 3.12+ (managed with `uv`)
* **Primary Language**: Python
* **Package / Build Tool**: `uv`

---

## 2. Deterministic Command Matrix

Agents must **never guess commands**. Use the exact CLI invocations below:

| Action | Command (PowerShell) | Command (Bash / POSIX) | Description |
| :--- | :--- | :--- | :--- |
| **Full Verify** | `./scripts/verify.ps1` | `./scripts/verify.sh` | **Runs ruff linter + format check + pytest in one gate.** |
| **Build / Sync**| `uv sync --extra dev` | `uv sync --extra dev` | Synchronizes virtual environment and dependencies |
| **Test All** | `uv run pytest` | `uv run pytest` | Executes the complete test suite |
| **Test Single** | `uv run pytest tests/<test_file>.py` | `uv run pytest tests/<test_file>.py` | Run a specific test file or filter |
| **Lint Check** | `uv run ruff check .` | `uv run ruff check .` | Checks code style without mutating |
| **Format Check**| `uv run ruff format --check .` | `uv run ruff format --check .` | Verifies formatting |
| **Format / Fix**| `uv run ruff check --fix . ; uv run ruff format .` | `uv run ruff check --fix . && uv run ruff format .` | Automatically fixes formatting & linter issues |

---

## 3. Inviolable Guardrails

1. **Verify Before Completion**:
   * Never declare a task complete or ask for review without running the **Full Verify** command (`./scripts/verify.ps1` or `./scripts/verify.sh`).
   * If verification fails, inspect stderr, fix the issue, and rerun until 100% green.

2. **No Hallucinated Dependencies**:
   * Do not add external packages or libraries to `pyproject.toml` without explicit user consent or an approved Architecture Decision Record in `docs/adr/`.
   * Always pin or set sensible version floors for Python dependencies.

3. **Preserve Architecture & ADRs**:
   * Review `docs/adr/` and `docs/architecture/overview.md` before introducing new abstractions, providers, or review stages.
   * Maintain the separation between:
     - `ci_code_reviewer.config`: Configuration models and YAML/env parsing.
     - `ci_code_reviewer.models`: Structured diffs, reviews, and comment schemas.
     - `ci_code_reviewer.harness`: Abstract agent harness (`ReviewHarness`) and concrete runners (`NativeReviewHarness`, `StrandsReviewHarness`).
     - `ci_code_reviewer.providers`: LiteLLM integration and authentication resolvers (BYOK & subscription bridges).
     - `ci_code_reviewer.integrations`: GitHub API PR diff extraction and comment publishing.

4. **Test Discipline (No Lazy Asserts)**:
   * Unit tests must test genuine business logic and edge cases. Never write trivial asserts like `assert True` or empty test stubs to bypass verification gates.

---

## 4. Spec-Driven Development (SDD) Workflow

For non-trivial features, avoid conversational "vibe coding". Follow the 4-stage pipeline:

```
specs/active/spec.md  ──▶  specs/active/plan.md  ──▶  specs/active/tasks.md  ──▶  Implement & Verify
  (Intent & Rules)           (Architecture/Files)       (Atomic Checklist)          (Deterministic Gate)
```

1. **Specify (`spec.md`)**: Define user stories, functional requirements, and edge cases.
2. **Plan (`plan.md`)**: Outline technical design, files to create/touch, and potential failure modes.
3. **Tasks (`tasks.md`)**: Break the plan into numbered, atomically testable micro-tasks (`[ ] 1. ...`).
4. **Execute**: Work through one task at a time, checking boxes (`[x]`) only after verifying changes with `./scripts/verify.ps1`.

---

## 5. Commit Style

All git commits must follow the **Conventional Commits** specification:
* `feat(scope): add user authentication endpoint`
* `fix(scope): handle null pointer in payment gateway response`
* `test(scope): add unit tests for discount calculator`
* `refactor(scope): extract token validation to middleware`
* `docs(scope): update ADR 0002 with caching strategy`
