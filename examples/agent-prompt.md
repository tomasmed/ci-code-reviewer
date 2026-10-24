# Agent Prompt for External Repositories

If you want an AI agent (Cursor, Claude Code, GitHub Copilot, Antigravity, Aider) in any other repository to configure **CI Code Reviewer**, simply give it this prompt:

---

### Copy-Paste Prompt:

> *"Configure our repository for automated agentic PR reviews using `tomasmed/ci-code-reviewer`.*
>
> *Please do the following:*
> *1. Create `.github/workflows/code-review.yml` using `tomasmed/ci-code-reviewer@v1` triggered on pull_request events, with `contents: read` and `pull-requests: write` permissions.*
> *2. Create `.ci-reviewer.yml` tailored to our tech stack with appropriate file ignore patterns (e.g., lockfiles, build output) and custom architecture guidelines.*
> *3. Configure the model to `anthropic/claude-3-5-sonnet-20241022` (or specify your preferred model).*
> *4. Remind me which GitHub Secret to add in repository settings (e.g., `ANTHROPIC_API_KEY`)."*

---

### What The Agent Will Generate:

1. **Workflow**: `.github/workflows/code-review.yml`
2. **Config**: `.ci-reviewer.yml`
3. **Secrets Setup**: Prompting the human developer to store `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in GitHub Repository Secrets.
