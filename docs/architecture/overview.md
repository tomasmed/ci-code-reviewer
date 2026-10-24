# CI Code Reviewer — System Architecture & Modularity

* **Project**: CI Code Reviewer (`ci-code-reviewer`)
* **Status**: Initialized
* **Primary Language**: Python 3.12+ (uv)

---

## 1. System Purpose & Vision

`ci-code-reviewer` is an open-source, agentic code reviewer designed to run as a GitHub Action, CI/CD pipeline step, or local CLI runner.

Its core objectives are:
1. **High Signal, Zero Noise**: Avoid trivial formatting and lint comments already handled by formatters. Focus on architectural drift, spec compliance, security/OWASP vulnerabilities, and anti-lazy-assert test efficacy.
2. **Bring Your Own Key (BYOK)**: Connect to any LLM provider (Claude, GPT, Gemini, Bedrock, DeepSeek) or local weights (Ollama, vLLM) via **LiteLLM**.
3. **Pluggable Agent Harness**: Dual-mode engine supporting ultra-fast native LiteLLM execution or AWS Strands (`strands-agents`) for MCP and tool orchestration.
4. **Subscription Bridging Layer**: Extensible auth architecture designed to accommodate consumer subscriptions (Claude Code CLI sessions, Copilot tokens, proxy bridges).
5. **Frictionless Consumer Integration**: Drop-in `.github/workflows/code-review.yml` and `.ci-reviewer.yml` for any target repository.

---

## 2. Data Flow & Review Pipeline

```
                               Pull Request Event
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     GitHub Ingestion Engine       │
                     │  - Fetch PR Diff & Metadata       │
                     │  - Filter ignored patterns        │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     Context Aggregator Layer      │
                     │  - In-repo ADRs (docs/adr/)       │
                     │  - Architecture guides            │
                     │  - Repo rules (.ci-reviewer.yml)  │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │       Review Agent Harness        │
                     │  - Native LiteLLM / AWS Strands   │
                     │  - Rubric Persona (Reviewer)      │
                     │  - Security & Anti-Lazy-Assert    │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │    Structured Assessment Result   │
                     │  - Executive Summary              │
                     │  - Critical Blockers              │
                     │  - Non-blocking Suggestions       │
                     │  - Recommendation (APPROVE/etc.)  │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     GitHub API Publisher Layer    │
                     │  - PR Top-level Markdown Review   │
                     │  - Inline Line-Specific Comments  │
                     └───────────────────────────────────┘
```

---

## 3. Directory Layout & Module Responsibilities

```text
src/ci_code_reviewer/
├── cli.py             # Typer CLI commands (review, version, validate-config)
├── config.py          # Pydantic configuration parser for .ci-reviewer.yml
├── models.py          # Schemas: ReviewComment, ReviewAssessment, Recommendation
├── harness/           # Pluggable Agent Orchestration Layer
│   ├── base.py        # Abstract Base Class: ReviewHarness
│   ├── factory.py     # Factory resolver: get_harness("strands" | "maf" | "native")
│   ├── native.py      # Sub-second LiteLLM direct agent runner
│   ├── strands.py     # AWS Strands SDK adapter with MCP tool capabilities
│   └── maf.py         # Microsoft Agent Framework (MAF) multi-agent runner
├── providers/         # Model and Auth layer
│   ├── litellm.py     # LiteLLM client wrapper with budget & fallback logic
│   └── auth.py        # Pluggable AuthStrategy (API keys, Ollama, session bridge)
├── context/           # Repo context extraction
│   ├── git_diff.py    # Git diff parsing, hunk extraction, file filtering
│   └── repo_context.py# Extracts ADRs, AGENTS.md, and repo architecture rules
└── integrations/      # External platform adapters
    └── github.py      # GitHub REST API client (PR diff fetching, review posting)
```

### Module Boundary Rules:
1. **Providers & Integrations are Isolated**: Core harnesses and models never directly call external HTTP endpoints; they interact via abstract interfaces.
2. **Deterministic Fallbacks**: If the agent harness fails or hits rate limits, the system fails gracefully with an informative error rather than crashing the CI build.
3. **No Secret Leaks**: Credentials, API tokens, or session headers must never be echoed to output logs or PR comments.

---

## 4. Key Configurations (`.ci-reviewer.yml`)

Consumer repositories configure behavior via `.ci-reviewer.yml`:

```yaml
version: "1"
model: "anthropic/claude-3-5-sonnet-20241022"
harness: "native" # or "strands"

filters:
  ignore_patterns:
    - "**/*.lock"
    - "**/dist/**"
  max_diff_lines: 3000

rules:
  require_tests: true
  check_security: true
  check_architecture: true
  custom_guidelines:
    - "Enforce strict error boundary handling in React components."
```
