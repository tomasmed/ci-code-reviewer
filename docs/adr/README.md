# Architecture Decision Records (ADRs)

This directory maintains the Architectural Decision Records for `ci-code-reviewer` using the [MADR](https://adr.github.io/madr/) format.

## Index of Decisions

| ADR | Title | Status | Date |
| :--- | :--- | :--- | :--- |
| [0001](0001-record-architecture-decisions.md) | Record Architecture Decisions | Accepted | 2026-10-24 |
| [0002](0002-technology-stack-and-agent-harness.md) | Adopt Python (uv), LiteLLM Provider Layer, and Pluggable Harness (AWS Strands + Native) | Accepted | 2026-10-24 |

## Guidelines

- To propose a new architectural decision, copy `template.md` to `XXXX-short-title.md`.
- Keep ADRs immutable once accepted. If a decision changes, create a new record that explicitly supersedes the former one.
