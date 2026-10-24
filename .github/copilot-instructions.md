# GitHub Copilot Instructions

All agent operating standards, commands, guardrails, and spec workflows are defined in [AGENTS.md](../AGENTS.md).

Always:
- Validate code changes with `./.github/scripts/verify.ps1` (or `./.github/scripts/verify.sh`).
- Check `docs/adr/` before suggesting new packages or structural patterns.
- Follow spec guidelines in `specs/README.md`.
- Follow PR review rules in `.agents/pr-reviewer.md`.
