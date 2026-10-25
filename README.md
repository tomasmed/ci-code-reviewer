# 🤖 CI Code Reviewer

An open-source, agentic code reviewer that plugs directly into **GitHub Actions**, CI/CD pipelines, and local developer workflows.

Built on a pluggable agent harness supporting **AWS Strands** and a lightweight **Native LiteLLM** engine, `ci-code-reviewer` enables **Bring Your Own Key (BYOK)** across 100+ commercial and local AI models (Anthropic Claude, OpenAI, Google Gemini, Ollama, AWS Bedrock).

---

## 🌟 Key Features

* **High Signal, Zero Noise**: Ignores formatting, whitespace, and linting trivia that automated formatters (`ruff`, `biome`, `prettier`) already handle. Focuses purely on logic bugs, security/OWASP flaws, architectural drift, and test integrity.
* **In-Repo Review Lenses (Sub-Agent Turns)**: Decomposes PR reviews into specialized perspectives (e.g. ADR conformance, stored-procedure-only data access rules, AppSec) executed as sub-agent turns with file-pattern triggers and in-repo context injection.
* **Anti-Lazy-Assert Test Auditing**: Scrutinizes test changes to catch hollow assertions (`assert True`, empty mocks, or tests that bypass real logic).
* **Multi-Harness Architecture (Launch Support for Strands & MAF)**:
  * **AWS Strands (`strands`)**: Powered by AWS's **Strands Agents** (`strands-agents`), supporting Model Context Protocol (MCP) tools, Cedar-based sandboxing, and dynamic tool calling.
  * **Microsoft Agent Framework (`maf`)**: Powered by Microsoft's unified **Agent Framework** (`agent-framework`), offering AutoGen-style conversational multi-agent review teams and enterprise coordination.
  * **Native Engine (`native`)**: Sub-second startup time on ephemeral CI runners via direct `litellm` and `pydantic`.
* **Universal BYOK (Bring Your Own Key)**: Powered by LiteLLM. Use Claude 3.5 Sonnet, GPT-4o, Gemini 2.0, DeepSeek R1, or air-gapped local models via **Ollama**.
* **Subscription Bridging Layer**: Extensible auth architecture designed to support consumer subscriptions (Claude Code session tokens, GitHub Copilot tokens, and OAuth bridges).
* **Zero-Friction Adoption**: Drop a 15-line GitHub Action into any repository or point an AI coding assistant at this repo to auto-configure.

---

## 🚀 Quick Start: Add to Any GitHub Repository

Add `.github/workflows/code-review.yml` to your repository:

```yaml
name: Agentic Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run CI Code Reviewer
        uses: tomasmed/ci-code-reviewer@v1
        with:
          model: "anthropic/claude-3-5-sonnet-20241022"
          github_token: ${{ secrets.GITHUB_TOKEN }}
          config_path: ".ci-reviewer.yml"
        env:
          # Add the API key for your chosen model in GitHub Secrets
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          # Or OPENAI_API_KEY / GEMINI_API_KEY
```

> 💡 **Tip**: Add `.ci-reviewer.yml` to your repo root to customize ignore patterns, review depth, and repo-specific architecture guidelines.

---

## ⚙️ In-Repo Configuration (`.ci-reviewer.yml`)

Repositories can fine-tune review behavior by placing a `.ci-reviewer.yml` in their repository root:

```yaml
version: "1"

# Target LLM (LiteLLM provider/model notation)
model: "anthropic/claude-3-5-sonnet-20241022"

# Agent harness: "native" (fastest) or "strands" (AWS Strands with MCP tools)
harness: "native"

filters:
  ignore_patterns:
    - "**/*.lock"
    - "**/pnpm-lock.yaml"
    - "**/package-lock.json"
    - "**/poetry.lock"
    - "**/uv.lock"
    - "**/dist/**"
    - "**/build/**"
    - "**/*.min.js"
  max_diff_lines: 3000

rules:
  # Flag pull requests that add complex logic without test coverage
  require_tests: true

  # Check for OWASP Top 10 vulnerabilities and hardcoded secrets
  check_security: true

  # Cross-reference with in-repo docs/adr/ and architecture rules
  check_architecture: true

  # Custom guidelines specific to your codebase
  custom_guidelines:
    - "Never use raw SQL queries in controller or route handler code."
    - "Ensure all database schema changes include backwards-compatible migrations."
    - "Strict null-checks required on external webhook payloads."
```

---

## 🏗️ Architecture & Data Flow

```
                               Pull Request Event
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     GitHub Ingestion Engine       │
                     │  - Fetch PR Diff & Metadata       │
                     │  - Filter ignored files & hunks   │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     Context Aggregator Layer      │
                     │  - In-repo ADRs (docs/adr/)       │
                     │  - AGENTS.md / Architecture Docs  │
                     │  - Repo rules (.ci-reviewer.yml)  │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │       Review Agent Harness        │
                     │  - Native LiteLLM / AWS Strands   │
                     │  - Rubric Persona Evaluation      │
                     │  - Security & Anti-Lazy-Assert    │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     GitHub API Publisher Layer    │
                     │  - PR Top-level Markdown Review   │
                     │  - Inline Line-Specific Comments  │
                     └───────────────────────────────────┘
```

For architectural specifications, see:
* [System Architecture Overview](docs/architecture/overview.md)
* [ADR 0002: Multi-Harness Technology Stack](docs/adr/0002-technology-stack-and-agent-harness.md)
* [Contributor Agentic SDLC & Ownership Guide](docs/workflows/agentic-sdlc.md)

---

## 💻 Local CLI Usage

You can run `ci-code-reviewer` directly from your terminal or in custom CI pipelines:

```bash
# Review a raw git diff
git diff main...HEAD > my_feature.diff
uvx ci-code-reviewer review --diff-file my_feature.diff --model openai/gpt-4o

# Review a GitHub PR with dry-run (prints findings to terminal without commenting)
uvx ci-code-reviewer review --pr 42 --dry-run
```

---

## 🔑 LLM Provider Routing & Model Formats

`ci-code-reviewer` relies on **LiteLLM** for provider routing. Ensure your model identifiers and environment variables match:

| Provider | Model Identifier Format | Required Env Var | Notes |
| :--- | :--- | :--- | :--- |
| **Google AI Studio** | `gemini/gemini-2.0-flash`<br>`gemini/gemini-1.5-flash` | `GEMINI_API_KEY` | **Must include `gemini/` prefix**. Omitting the prefix routes to Vertex AI (requiring GCP project credentials) and causes HTTP 404. |
| **Anthropic** | `anthropic/claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` | High reasoning fidelity and ADR conformance. |
| **OpenAI** | `openai/gpt-4o`<br>`openai/gpt-4o-mini` | `OPENAI_API_KEY` | Fast structured output evaluation. |
| **Ollama (Local)** | `ollama/qwen2.5-coder:7b` | _None_ | Set `api_base: "http://localhost:11434"` in config. |

> ⚠️ **Troubleshooting HTTP 404 with Gemini**: If Google AI Studio returns 404:
> 1. Check for the `gemini/` prefix (e.g., `gemini/gemini-2.0-flash`, not `gemini-2.0-flash`).
> 2. Verify the model ID is active in your Google AI Studio project (some snapshots or experimental tiers may require `gemini/gemini-1.5-flash` or newer general releases).
> 3. Verify `GEMINI_API_KEY` is set in GitHub repository secrets and forwarded in your workflow step `env:`.

---

## 🛡️ Reliability & Fail-Open Stance (Open Stance)

CI pipelines should **never block developer merges** due to transient third-party LLM outages, rate limits (HTTP 429), or misconfigured model keys.

`ci-code-reviewer` adopts a **Fail-Open Stance** ([ADR 0003](docs/adr/0003-fail-open-stance-and-degraded-provider-fallback.md)):
* If an LLM provider endpoint is unreachable or returns an error, the review harness completes in **fallback mode**.
* The GitHub Actions job exits with code `0` to keep CI green and prevent blocking deployments.
* The exact provider error (e.g. `NotFoundError: 404`) is prominently printed to CI console logs and recorded in PR comments.
* The review assessment emits an advisory **COMMENT** rather than a misleading clean **APPROVE**, ensuring transparent visibility.

---

## 🤖 Ask Your Coding Agent to Set It Up

If you are using Cursor, Claude Code, GitHub Copilot, or Antigravity in an external repository, simply prompt it:

> *"Set up automated code reviews for this repository using `tomasmed/ci-code-reviewer`. Create `.github/workflows/code-review.yml` and a `.ci-reviewer.yml` tailored to our tech stack."*

See [`examples/agent-prompt.md`](examples/agent-prompt.md) for full instructions.

---

## 🛠️ Contributing & Development

This repository uses **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/) for high-velocity development.

```bash
# Clone the repository
git clone https://github.com/tomasmed/ci-code-reviewer.git
cd ci-code-reviewer

# Sync dependencies & virtual environment
uv sync --extra dev

# Run the deterministic verification gate (lint + format check + tests)
./.github/scripts/verify.ps1   # Windows PowerShell
./.github/scripts/verify.sh    # macOS / Linux
```

All contributions must pass the deterministic verification gate and adhere to [AGENTS.md](AGENTS.md).

---

## 📄 License

This project is licensed under the **Mozilla Public License 2.0 (MPL-2.0)**. See [`LICENSE`](LICENSE) for details.
* **Free to use & integrate**: Anyone can run `ci-code-reviewer` in their open-source or commercial CI/CD pipelines without legal friction or viral license contamination.
* **Protected & Reciprocal**: Modifications to this project's code must remain free, open source, and contributed back under MPL 2.0.
