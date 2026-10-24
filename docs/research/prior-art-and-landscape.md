# Prior Art & Competitive Landscape: Automated & Agentic Code Reviewers

* **Date**: October 2026
* **Project**: CI Code Reviewer (`ci-code-reviewer`)
* **Author**: tomasmed & Agentic Engineering Team

---

## 1. Executive Overview

Automated code review has evolved through three distinct waves:
1. **Wave 1: Static Analysis & Linters (2000s–2020)**: Tools like SonarQube, ESLint, Ruff, Checkstyle. They excel at deterministic rule checks, syntax, and formatting, but have zero awareness of business logic, architectural drift, or edge-case handling.
2. **Wave 2: First-Generation LLM Wrappers (2023–2024)**: Single-shot prompt tools (like basic GitHub Actions that dump a `git diff` into `gpt-3.5-turbo` or `gpt-4`). These produced high-noise reviews, nitpicking code formatting (already caught by linters) or halluncinating false positives.
3. **Wave 3: Agentic Code Review Systems (2025–Present)**: Multi-step reasoning systems capable of retrieving repository architecture and ADRs, auditing test efficacy (anti-lazy-asserts), evaluating security, and calling tools or linters iteratively.

**CI Code Reviewer** is designed as the premier **open-source, multi-harness agentic code reviewer**, offering launch support for both **AWS Strands** and **Microsoft Agent Framework (MAF)**, backed by **LiteLLM** for universal Bring-Your-Own-Key (BYOK) and local model execution.

---

## 2. Deep Dive: Existing Prior Art

### A. Qodo / Codium PR-Agent (`qodo-ai/pr-agent`)
* **Type**: Open-Source (with commercial cloud offering)
* **Architecture**: Monolithic Python application with command-driven triggers (`/review`, `/describe`, `/improve`). Directly calls OpenAI/LiteLLM.
* **Strengths**:
  * Established open-source brand; supports GitHub, GitLab, Bitbucket.
  * Good collection of PR commands (`/ask`, `/generate_labels`).
* **Limitations & Gaps**:
  * **Monolithic Prompting**: Heavily relies on large Jinja prompt templates rather than modular agentic frameworks.
  * **No Multi-Harness Support**: Locked into its internal pipeline; cannot easily switch to modern agent runtimes like AWS Strands or Microsoft Agent Framework.
  * **Heavy Runtime Weight**: The container image and dependency graph are large, resulting in slower startup times in standard CI runners.
  * **Noise Calibration**: Frequently comments on stylistic choices unless heavily tuned with complex configuration files.

### B. CodeRabbit
* **Type**: Commercial Closed-Source SaaS
* **Architecture**: Proprietary cloud service. Chunks git diffs using AST parsing, summarizes changes, and generates both top-level PR reviews and inline comments.
* **Strengths**:
  * Industry standard for developer UX: clean PR summaries, collapsible change walkthroughs, poem generation, and interactive chat replies on PR comments.
  * Astute hunk positioning and context gathering.
* **Limitations & Gaps**:
  * **Closed Source & Expensive**: Costs $15–$30/developer/month; prohibitive for open-source communities, hobbyists, and cost-conscious organizations.
  * **Privacy & Data Residency**: Code must be sent to CodeRabbit's cloud infrastructure. Self-hosted options require high-tier enterprise contracts.
  * **No True BYOK / Local Models**: Cannot natively run with local Ollama/vLLM instances on air-gapped CI runners without enterprise setup.

### C. Greptile
* **Type**: Commercial Closed-Source SaaS
* **Architecture**: Indexes the entire codebase into a vector and graph database to answer queries and review PRs with full repo awareness.
* **Strengths**:
  * High context awareness across disparate files and modules.
* **Limitations & Gaps**:
  * Requires full initial indexing time and continuous synchronization.
  * Closed-source, high pricing tiers.

### D. GitHub Copilot PR Summaries & Workspace
* **Type**: Native GitHub Feature
* **Architecture**: Integrated into github.com; generates PR descriptions and light summaries.
* **Strengths**:
  * Zero setup for existing GitHub Enterprise / Copilot customers.
* **Limitations & Gaps**:
  * Passive summarizer rather than a critical code reviewer. Does not challenge architecture, does not check test integrity, and does not block PRs on critical vulnerabilities.

### E. Sweep AI / Mentat / Aider
* **Type**: AI Coding Agents
* **Architecture**: Focused on *writing* code from bug reports or user prompts rather than serving as an objective, skeptical *reviewer* in CI.

---

## 3. Comparative Matrix

| Feature | `ci-code-reviewer` | Qodo PR-Agent | CodeRabbit | Greptile | GitHub Copilot |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Open Source** | **100% Apache-2.0** | Open Core | Closed Source | Closed Source | Closed Source |
| **Harness Architecture** | **Pluggable (AWS Strands + MAF + Native)** | Monolithic internal | Proprietary SaaS | Proprietary SaaS | Proprietary SaaS |
| **BYOK (Bring Your Own Key)** | **Universal via LiteLLM (100+ models)** | Supported | None (SaaS billing) | None (SaaS billing) | Tied to Copilot seat |
| **Local Models (Ollama/vLLM)** | **First-class, zero-cost** | Partial | No | No | No |
| **In-Repo Context (ADRs / AGENTS.md)**| **Native first-class** | Custom instructions | Custom prompt | Codebase index | Minimal |
| **Anti-Lazy-Assert Auditing** | **Built into review rubric** | No | Partial | No | No |
| **CI Runner Startup Overhead** | **Sub-second (Native)** | ~20–40s container pull | Cloud webhook (0s runner) | Cloud webhook | Native web UI |
| **Subscription Bridging (BYOA)** | **Extensible Auth Strategy** | No | No | No | Copilot seat only |

---

## 4. Key Differentiators for `ci-code-reviewer`

1. **Dual-Harness Launch Support (AWS Strands & Microsoft Agent Framework)**:
   * **AWS Strands**: Provides native Model Context Protocol (MCP) tool integration, Cedar-based security sandboxing, and lightweight agent loops.
   * **Microsoft Agent Framework (MAF)**: Provides enterprise-grade orchestration, multi-agent chat topologies (inherited from AutoGen), and type safety.
   * **Native Mode**: Instant execution for resource-constrained CI environments.
2. **Anti-Noise Rubric**:
   * Specifically instructs the reviewer to discard anything that formatters (`ruff`, `biome`) or linters would catch.
   * Evaluates pull requests against 4 pillars: Logic Correctness, Test Integrity (Anti-Lazy-Assert), Architectural Conformance (`docs/adr/`), and OWASP Security.
3. **True Privacy & Air-Gapped Support**:
   * Works on local Ollama endpoints with zero network exposure of proprietary source code.
4. **Dogfood-First Velocity**:
   * Tested on User 0 repositories before any public distribution.
