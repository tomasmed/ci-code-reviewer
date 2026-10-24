# Feature Specification: GitHub PR Ingestion, Publishing, & Workspace Blast Radius (with MAF Multi-Lens Support)

* **Status**: Approved
* **Target Release / Milestone**: v0.2.0 / v1
* **Associated Scope**: GitHub Actions Integration, Local Workspace Blast Radius Analysis, & Microsoft Agent Framework (MAF) Lens Alignment

---

## 1. Context & Business Intent

* **Problem**:
  1. `ci-code-reviewer` currently has review lens abstractions, but `cli.py` is a stub that prints placeholder text and exits.
  2. Traditional CI review bots only inspect the isolated 3-line diff hunks provided by webhooks or REST APIs. When a PR alters a helper function, interface, or method signature, downstream callers and business logic outside the diff hunks break silently.
  3. Because the GitHub Actions runner already checks out the repository (`actions/checkout` with `fetch-depth: 0`), our agent has direct, zero-cost access to the complete codebase on disk. Failing to leverage the local workspace leaves a massive blind spot.
  4. The Microsoft Agent Framework (`maf`) harness must ship with v1 supporting this exact multi-lens review pipeline and local workspace inspection capabilities.

* **User Story**:
  As a developer or DevOps engineer, I want to add `uses: tomasmed/ci-code-reviewer@v1` to my GitHub Action workflow in any repository so that incoming PRs are reviewed not only for local diff syntax, but also for downstream breaking changes and caller impact across the entire codebase, with findings published directly to the pull request.

---

## 2. Functional Requirements

### 1. GitHub PR Ingestion & Local Git Resolution
- **Hybrid Diff Extraction**:
  - Prefer extracting the PR diff directly from the local git checkout (`git diff origin/<base>...HEAD` or `git diff <base_sha>...<head_sha>`).
  - Fall back to GitHub REST API (`GET /repos/{owner}/{repo}/pulls/{number}` with `Accept: application/vnd.github.v3.diff`) if local git history is unavailable.
- Retrieve PR metadata (head commit SHA, base branch, PR title/author) from GitHub REST API.
- Support `GITHUB_TOKEN` and `GITHUB_REPOSITORY` from environment variables or CLI flags.
- Respect `FilterConfig` (ignore lock files, generated assets, minified bundles).

### 2. Workspace Awareness & Downstream Blast Radius
- **Symbol & Caller Impact Detection**:
  - Analyze diff hunks for modified or deleted function signatures, class methods, types, or exported constants.
  - Search the local workspace (via AST or regex reference scanning) for usages and callers outside the diff hunks.
  - Inject discovered caller locations and surrounding context into the active review lens turn (e.g. `architecture_adrs`, `security_owasp`, or repo custom lenses).
- **Tool-Augmented Inspection (MAF & Strands)**:
  - In `MafReviewHarness` (and `StrandsReviewHarness`), equip sub-agent turns with workspace inspection tools (`read_file`, `search_references`) so agents can autonomously verify downstream callers and imports when evaluating risk.

### 3. GitHub Review Publishing & Smart Comment Anchoring
- Format `ReviewAssessment` into a GitHub PR Review (`POST /repos/{owner}/{repo}/pulls/{number}/reviews`).
- Map `Recommendation` to review event:
  - `APPROVE` ➔ `APPROVE`
  - `REQUEST_CHANGES` ➔ `REQUEST_CHANGES`
  - `COMMENT` ➔ `COMMENT`
- **Smart Comment Anchoring (GitHub 422 Protection)**:
  - GitHub REST API rejects inline comments placed on files or lines not modified in the PR diff (`422 Unprocessable Entity`).
  - For downstream breaking changes, anchor the inline comment on the *diff line that caused the breakage* (e.g., the modified helper definition) citing the broken callers.
  - If any inline comment fails or cannot be anchored to a diff hunk, automatically consolidate it into a dedicated "Downstream Blast Radius & Unanchored Findings" section in the top-level review markdown body.
- Support `--dry-run`: render the full review assessment and blast radius report to console without calling the GitHub API.

### 4. Microsoft Agent Framework (MAF) Multi-Lens Alignment
- `MafReviewHarness` executes sub-agent personas per active lens matching `NativeReviewHarness`.
- Passes workspace context and lens definitions to MAF agents.
- Provides robust fallback/mocking when the optional `agent-framework` package is not installed so tests remain deterministic.

---

## 3. Boundary Conditions & Edge Cases

* **Large Repositories & Search Performance**: Blast radius symbol searches must be bounded to source files (honoring `FilterConfig.ignore_patterns`) with timeouts to avoid CI latency spikes.
* **Out-of-Hunk Line Numbers**: LLM findings that reference unchanged lines are safely absorbed into the main review markdown body rather than crashing the GitHub API call.
* **Empty / Non-Code Diffs**: Diffs modifying only documentation or ignored lock files produce clean approvals with zero unnecessary LLM token spend.
* **Detached HEAD / Shallow Clones**: If local git checkout lacks history, seamlessly fall back to GitHub REST API diff retrieval.
* **Missing Credentials**: Exit with informative human-friendly errors if `GITHUB_TOKEN` is missing when attempting to publish.

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] `GitHubClient` in `src/ci_code_reviewer/integrations/github.py` with PR diff fetching, metadata resolution, and review publishing.
- [ ] Workspace context & blast radius scanner in `src/ci_code_reviewer/context/` analyzing caller references across unchanged files.
- [ ] `cli.py review` command executes the full pipeline end-to-end for `--pr` and `--diff-file`.
- [ ] `MafReviewHarness` in `src/ci_code_reviewer/harness/maf.py` implements multi-lens orchestration and produces compatible `ReviewAssessment`.
- [ ] `action.yml` exports `GITHUB_REPOSITORY: ${{ github.repository }}`.
- [ ] Comprehensive unit & integration tests for GitHub client, blast radius scanner, CLI review command, and MAF harness.
- [ ] Deterministic verification gate (`bash ./.github/scripts/verify.sh`) runs 100% green.
