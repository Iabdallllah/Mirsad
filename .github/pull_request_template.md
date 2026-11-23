<!-- Mirsad PR template — required by AGENTS.md §11 / plan.md §16.2 -->

## What changed

<!-- Concise description of the change. Link the milestone/task (plan.md §3.2). -->

Milestone / task:

## Why

<!-- Problem being solved; reference plan.md / design.md sections. -->

## Risk

<!-- Security, data, compatibility, and blast-radius assessment. -->

## Test evidence

<!-- Exact commands run + results (output excerpts, screenshots for UI).
     Distinguish implemented / tested / verified-in-staging. -->

- [ ] Lint + typecheck pass
- [ ] Unit / integration tests pass
- [ ] Security-relevant tests pass (RLS, egress, sanitizer, HMAC — as applicable)
- [ ] Playwright updated for changed journeys (`data-testid` per design.md §13.4)

## Screenshots (UI changes)

<!-- Dark theme, 1440px + 375px. No secrets/PII visible. -->

## Rollback plan

<!-- How to revert safely; migration compatibility notes if applicable. -->

## Remaining unverified items

<!-- Explicit list or "none". Never omit (AGENTS.md §13). -->
