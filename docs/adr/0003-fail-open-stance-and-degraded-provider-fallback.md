# 0003: Fail-Open Stance and Degraded Provider Fallback

* **Status**: accepted
* **Deciders**: core team
* **Date**: 2026-10-25
* **Technical Story**: Dogfooding review on JlightCalendar PR #26 and handling upstream LLM provider outages / 404 model errors

## Context and Problem Statement

Automated CI review bots depend on remote third-party LLM APIs (LiteLLM, Anthropic, OpenAI, Google AI Studio, Bedrock). These external dependencies inevitably encounter:
- Transient network blips or provider rate limits (429 Too Many Requests).
- Deprecated or misconfigured model strings (e.g. HTTP 404 from Google AI Studio / Gemini API).
- Quota exhaustion or temporary upstream downtime.

If a code review bot crashes or halts the CI pipeline with a non-zero exit code on provider failures ("fail-closed"), it creates immediate developer friction: developers cannot merge clean pull requests, deploy urgent hotfixes, or proceed through automated staging pipelines.

Conversely, if the harness silently succeeds and emits a formal "Verdict: Approved (0 blockers found)", it gives teams a false sense of security that their diff was thoroughly reviewed when no active inspection actually took place.

## Decision Drivers

* **Zero CI Disruptions**: Developer pipelines and emergency deployments must never be hard-blocked by an external LLM vendor outage.
* **Transparent Review Diagnostics**: Any failure to connect to an LLM must be visibly surfaced in CI logs and PR summaries with the exact error cause (e.g. HTTP 404, auth error).
* **Honest Evaluation Signals**: An unreviewed PR due to provider failure must never masquerade as a verified "Clean Approval".

## Considered Options

* **Option 1 (Fail-Closed / Hard Error)**: Crash the GitHub Action with exit code 1 whenever an LLM call fails.
* **Option 2 (Silent Fail-Open / Blind Approval)**: Catch all exceptions, swallow error traces, and submit a standard `APPROVE` verdict.
* **Option 3 (Degraded Fail-Open Stance with Transparent Fallback & Advisory Comment)**: Keep CI green (exit code 0), capture and log upstream error causes, emit a non-blocking advisory comment (`Recommendation.COMMENT`), and mark the assessment with clear fallback notices.

## Decision Outcome

Chosen option: **Option 3: Degraded Fail-Open Stance with Transparent Fallback & Advisory Comment**.

When an LLM provider call fails:
1. The harness captures the exception (`e`) and records the failure reason in `LensTurnResult.summary`.
2. The CLI surfaces a visible warning in CI logs: `⚠️ Notice: Lens '{name}' - {summary}`.
3. If all lenses operate in fallback mode, the assessment verdict defaults to an advisory **COMMENT** rather than a formal **APPROVE**, ensuring no false stamp of approval is cast.
4. The PR comment explicitly states:
   > "Notice: All lenses operated in open-stance fallback mode due to upstream provider/model error. Active LLM inspection was bypassed."
5. The GitHub Actions job exits with code 0 so CI checks remain green and unblocked.

### Positive Consequences

* **Developer Velocity Preserved**: External LLM downtime never halts release workflows or PR merges.
* **Instant Root Cause Debugging**: Developers inspecting CI logs immediately see whether a failure was caused by HTTP 404, bad API keys, or rate limits without needing access to provider dashboards.
* **Audit Integrity**: Review logs accurately reflect that code was bypassed due to provider unavailability rather than falsely claiming 0 blockers.

### Negative Consequences / Trade-offs

* PRs merged during an LLM outage will not have automated code review comments until the provider issue is resolved. Teams requiring mandatory AI reviews must configure separate branch protection rules.

## Links & References

* Dogfooding discovery: JlightCalendar PR #26 (Gemini 404 model routing)
* LiteLLM Provider Routing & Error Handling: `https://docs.litellm.ai/docs/providers`
