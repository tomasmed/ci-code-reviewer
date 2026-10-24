# 0002. Adopt Python (uv), LiteLLM BYOK Provider Layer, and Pluggable Agent Harness (AWS Strands + Native)

* **Status**: accepted
* **Deciders**: tomasmed, Agentic Engineering Team
* **Date**: 2026-10-24
* **Technical Story**: Architecture foundation for open-source CI code reviewer

## Context and Problem Statement

We are creating an open-source agentic code reviewer intended to run inside GitHub Actions and CI/CD pipelines. The system must:
1. Review pull requests with deep context (code diffs, in-repo ADRs, test efficacy, OWASP security guardrails) rather than superficial formatting nitpicks.
2. Allow users to Bring Your Own Key (BYOK) across any LLM (Claude, GPT, Gemini, Bedrock) or run locally using open-source weights (Ollama, vLLM).
3. Provide an architecture extensible toward subscription bridging (e.g. Claude Code session tokens, GitHub Copilot subscriptions).
4. Run with minimal startup latency inside ephemeral CI runners (such as GitHub-hosted `ubuntu-latest`).
5. Be trivially pullable/configurable by any repository with a simple GitHub Actions workflow or agent prompt.

## Decision Drivers

* **Startup & Execution Speed in CI**: Ephemeral CI runners incur per-minute billing and developer wait time. Heavy frameworks with hundreds of dependencies slow down PR checks.
* **Model Agnosticism**: Avoid vendor lock-in; allow developers and enterprises to use their preferred models or air-gapped local setups.
* **Extensible Agent Capabilities**: Support tool-calling, MCP (Model Context Protocol), and multi-turn reasoning without locking the entire architecture to a single rigid framework.

## Considered Options

* **Option 1**: Heavyweight LangChain / LangGraph orchestration.
* **Option 2**: Pure single-shot script with raw vendor SDKs (e.g. only `anthropic` or `openai` SDK).
* **Option 3**: **Pluggable Harness Architecture** with:
  - **Toolchain**: Python 3.12+ managed by `uv` (lightning-fast installs and virtual environment syncing).
  - **Model Abstraction**: **LiteLLM** for universal BYOK across 100+ providers and Ollama support.
  - **Review Harness**: A dual-mode harness interface (`ReviewHarness`):
    - `NativeReviewHarness`: Default, lightweight, zero-overhead pipeline using LiteLLM structured outputs.
    - `StrandsReviewHarness`: Optional agentic harness using **AWS Strands** (`strands-agents`) for MCP tool integration, multi-agent swarms, and sandboxed tool calling.
  - **Auth Layer**: Pluggable `AuthStrategy` supporting direct API keys, local endpoints (Ollama), and planned session/subscription bridges (Claude Code / Copilot tokens).

## Decision Outcome

Chosen option: **Option 3**.

### Positive Consequences

* **Sub-second runner startup**: `uv` and `NativeReviewHarness` allow the GitHub Action to install and start reviewing in seconds rather than minutes.
* **Universal BYOK**: Developers configure one secret (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or local URL) and can switch models via a single string (`model: anthropic/claude-3-5-sonnet-20241022`).
* **Tool & MCP Support**: AWS Strands integration allows sophisticated reviews that query external APIs, check schemas, or use MCP tools when desired.
* **Zero Host Pollution**: Clean separation of core application logic from CI-specific runner scripts.

### Negative Consequences / Risks

* AWS Strands is an evolving SDK; maintaining an adapter requires keeping pace with upstream API updates.
* Subscription bridging (e.g. consumer Claude/ChatGPT tokens) is subject to upstream platform policy changes; standard API keys remain the primary supported path.

## Links

* [Agent Harness & Model Layer Research](../research/agent-harness-and-model-layer.md)
* [System Architecture Overview](../architecture/overview.md)
