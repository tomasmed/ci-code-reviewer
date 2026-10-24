# User 0 Dogfooding Playbook & Integration Strategy

* **Author**: tomasmed & Agentic Engineering Team
* **Target Repositories**: `tomasmed/*` repositories (User 0)
* **Goal**: Validate `ci-code-reviewer` in production CI across diverse tech stacks prior to public release.

---

## 1. Dogfooding Philosophy

Before asking the open-source community to trust `ci-code-reviewer` with their CI gates, we treat our own repositories as **User 0**.

### Core Hypotheses to Validate:
1. **Zero Hallucinated Noise**: Can the reviewer run on 20 consecutive pull requests without leaving trivial style/linter comments?
2. **Anti-Lazy-Assert Efficacy**: Can the reviewer reliably detect hollow assertions (e.g. `assert True`, superficial mocks) in unit tests?
3. **Multi-Harness Parity**: How does **AWS Strands** compare directly against **Microsoft Agent Framework (MAF)** on real code reviews in terms of reasoning depth, speed, and token cost?
4. **CI Speed Impact**: Does the action complete within acceptable PR CI budgets (<60s on average)?

---

## 2. Onboarding User 0 Repositories

### Step-by-Step Setup Ritual

For each User 0 repository owned by `tomasmed`:

```text
Repository Root
├── .github/workflows/
│   └── code-review.yml      # CI workflow calling tomasmed/ci-code-reviewer@v1
└── .ci-reviewer.yml         # In-repo configuration specifying rules & harness
```

#### Step 1: Add the Workflow (`.github/workflows/code-review.yml`)
```yaml
name: Agentic Code Review (Dogfood)

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
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run CI Code Reviewer
        uses: tomasmed/ci-code-reviewer@v1
        with:
          model: "anthropic/claude-3-5-sonnet-20241022"
          harness: ${{ matrix.harness || 'native' }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### Step 2: Tailor `.ci-reviewer.yml`
Customize the configuration for the repo's specific ecosystem (e.g. Next.js, .NET, Python, Go):
```yaml
version: "1"
model: "anthropic/claude-3-5-sonnet-20241022"
harness: "strands" # Alternate with "maf" or "native"

filters:
  ignore_patterns:
    - "**/*.lock"
    - "**/pnpm-lock.yaml"
    - "**/package-lock.json"
    - "**/dist/**"
  max_diff_lines: 3000

rules:
  require_tests: true
  check_security: true
  check_architecture: true
```

---

## 3. Dual-Harness Benchmarking Protocol (Strands vs MAF)

During the User 0 phase, we benchmark both launch harnesses on the same PRs:

| Metric | AWS Strands (`strands-agents`) | Microsoft Agent Framework (`maf`) | Native LiteLLM |
| :--- | :--- | :--- | :--- |
| **Runner Startup Time** | Measure runner bootstrap (s) | Measure runner bootstrap (s) | Sub-second baseline |
| **Total Review Latency** | Time to post GitHub review | Time to post GitHub review | Time to post GitHub review |
| **Token Consumption** | Total prompt + completion tokens | Total prompt + completion tokens | Minimal baseline |
| **Actionable Bugs Caught** | True positive blocker count | True positive blocker count | True positive blocker count |
| **False Positive Noise** | Unnecessary comments | Unnecessary comments | Unnecessary comments |
| **Anti-Lazy-Assert Accuracy**| Did it flag hollow test asserts? | Did it flag hollow test asserts? | Did it flag hollow test asserts? |

---

## 4. Feedback Loop & Triage Matrix

For every review generated during User 0 dogfooding:
* 👍 **High Signal**: Review caught a subtle race condition, missing null check, security leak, or hollow test.
* 👎 **Noise / False Positive**: Review commented on indentation, linting, or stylistic preference.
  * **Remediation**: Adjust rubric prompts in `SYSTEM_PROMPT` or refine regex / AST hunk filters.
* ⚡ **Performance Lag**: If any harness exceeds 90 seconds, profile tool calls and token payloads.
