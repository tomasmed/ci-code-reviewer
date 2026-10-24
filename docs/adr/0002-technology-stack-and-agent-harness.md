# 0002. Adopt Python (uv), LiteLLM Provider Layer, and Multi-Harness Architecture (AWS Strands + Microsoft Agent Framework + Native)

* **Status**: accepted
* **Deciders**: tomasmed, Agentic Engineering Team
* **Date**: 2026-10-24
* **Technical Story**: Architecture foundation for open-source CI code reviewer with launch support for AWS Strands and Microsoft Agent Framework (MAF).

## Context and Problem Statement

We are creating an open-source agentic code reviewer intended to run inside GitHub Actions and CI/CD pipelines. The system must:
1. Review pull requests with deep context (code diffs, in-repo ADRs, test efficacy, OWASP security guardrails) rather than superficial formatting nitpicks.
2. Allow users to Bring Your Own Key (BYOK) across any LLM (Claude, GPT, Gemini, Bedrock) or run locally using open-source weights (Ollama, vLLM).
3. Support multiple leading agent frameworks from day one, specifically launching with support for both **AWS Strands** (`strands-agents`) and the **Microsoft Agent Framework** (`agent-framework` / MAF), alongside an ultra-fast native engine.
4. Provide an architecture extensible toward subscription bridging (e.g. Claude Code session tokens, GitHub Copilot subscriptions).
5. Enable User 0 dogfooding across repository suites.

## Decision Drivers

* **Ecosystem Diversity**: Avoid vendor lock-in to a single agent SDK. Some teams operate within AWS environments (favouring Strands and Bedrock), while others operate in Microsoft/Azure environments (favouring MAF, AutoGen, and Semantic Kernel).
* **Startup & Execution Speed in CI**: Ephemeral CI runners require fast bootstrap.
* **Model Agnosticism**: Universal BYOK via LiteLLM.

## Considered Options

* **Option 1**: Lock exclusively to AWS Strands.
* **Option 2**: Lock exclusively to Microsoft Agent Framework (MAF) / AutoGen.
* **Option 3**: **Pluggable Multi-Harness Architecture** with launch support for:
  - **AWS Strands (`strands-agents`)**: For Model Context Protocol (MCP) tools, Cedar-sandboxed execution, and AWS/Bedrock native teams.
  - **Microsoft Agent Framework (`agent-framework` / MAF)**: For enterprise multi-agent coordination, AutoGen conversation topology, and Azure/OpenAI native teams.
  - **Native LiteLLM Engine**: For sub-second, zero-dependency CI runs.
  - **LiteLLM**: Universal BYOK provider abstraction across 100+ models.

## Decision Outcome

Chosen option: **Option 3**. Launching with first-class support for both **AWS Strands** and **Microsoft Agent Framework (MAF)**.

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
