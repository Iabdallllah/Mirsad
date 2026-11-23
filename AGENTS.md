# AGENTS.md — Mirsad Repository Rules for Coding Agents

| Field | Value |
|---|---|
| Applies to | Every AI coding agent, subagent, and human contributor in this repository |
| Status | Approved — effective immediately |
| Last updated | 2026-11-22 |
| Source of truth | Approved Product Brief v1.0 + `design.md` + `plan.md` |

> These rules are **non-negotiable**. If a task conflicts with them, stop and ask. Do not
> "interpret creatively" around security, scope, or truthfulness requirements.

---

## 1. Read before you change anything

**MUST**, before making any change:

1. Read **this `AGENTS.md` in full** — it is short and applies to every task.
2. Read **only the sections you need** from `design.md` and `plan.md`. Do **not** load either file in
   full by default (they are large — tens of KB; full reads waste the context window). Use the
   section index below, then open the specific sections for the current phase/task.
3. Read the relevant existing code, tests, and migrations for the area you are touching.
4. Check the current milestone in `plan.md` §3 and confirm the task belongs to it.

If the task is not in the approved scope, **stop and ask** — do not build "while we're here."

### Section index (read by task area, not whole files)

**`design.md`**

| Task area | Read |
|---|---|
| Any UI screen or flow | §4 IA, §5 journeys, §6 screens, §11 microcopy, §12 state matrix |
| Visual/component work | §3 brand, §7 components, §8 design tokens |
| Responsive or accessibility | §9 responsive, §10 accessibility |
| UI acceptance / Playwright selectors | §13 acceptance criteria + `data-testid` list |
| Android app | §4.4, §6.14, §9.2 |
| PDF report | §6.15 + §14 open items |

**`plan.md`**

| Task area | Read |
|---|---|
| Scope, phase, timeline | §1–§3 |
| Architecture, structure, stack | §4, §6, §7 |
| Data model, auth, RLS | §8, §9 |
| API contracts, integrations | §10, §11 |
| Env vars | §12 |
| Tests, security, monitoring | §13, §14, §15 |
| GitHub workflow, deployment | §16, §17 |
| Backup/DR/rollback | §18 |
| Release gates | §19 |
| Pricing/plan limits | §20 |
| Risks and open TBDs | §21, §22 |

**Reading rules:** if a section points to another section that you need, read that one too. If you
suspect two documents conflict, read the adjacent sections and **stop and report** — never guess.
Do not quote large excerpts of either document back into the conversation; summarize.

### Source-of-truth hierarchy

1. Approved Product Brief v1.0 (conversation record) — product decisions.
2. `design.md` — UX/UI behavior and visual rules.
3. `plan.md` — technical architecture, data model, deployment, gates.
4. `AGENTS.md` — agent behavior and repository rules.

If two documents conflict, stop and report the conflict. Never silently pick one.

---

## 2. Scope discipline

- **MUST** work only on approved milestones and tasks.
- **MUST** keep changes small, focused, and reversible.
- **MUST NOT** add features, pages, dependencies, services, or infrastructure that are not in
  `plan.md` §2 (MVP scope) without explicit approval.
- **MUST NOT** refactor unrelated code in the same change.
- **MUST NOT** rename public routes, database tables, API fields, or env vars without approval and a
  migration/compatibility plan.
- **MUST** prefer the smallest correct change over a broad rewrite.
- **MUST** leave the codebase in a working state at every commit.

**Out of scope unless explicitly approved:** payments, multi-user/RBAC, GitLab/Bitbucket/Slack/Jira,
public API, iOS, cloud/IaC scanning, asset discovery, shareable report links, 24/7 offensive
monitoring, SOC2, E&O insurance.

---

## 3. Truthfulness and evidence

- **MUST NOT** claim a feature works unless it has been run and tested.
- **MUST NOT** invent dependencies, APIs, provider capabilities, model names, or environment values.
- **MUST NOT** write "done", "fixed", or "verified" in a report without evidence (command output,
  test result, screenshot, or log).
- **MUST** mark unknown or unverified details as **TBD** or **Unverified** — never fabricate them.
- **MUST** distinguish "implemented", "tested", and "verified in staging/production".
- **MUST** report failures honestly, including flaky tests and environment limitations.
- **MUST NOT** copy marketing claims ("100% secure", "hacker-proof") into UI, docs, or code comments.

---

## 4. Secrets and credentials

- **MUST NOT** expose secrets, tokens, private keys, service-role keys, cookies, or customer data to:
  - the browser bundle,
  - the mobile app bundle,
  - GitHub (commits, PRs, issues, logs, Actions output),
  - application logs,
  - error trackers,
  - screenshots,
  - test fixtures or seed data.
- **MUST** keep `SUPABASE_SERVICE_ROLE_KEY`, GitHub App private keys, LLM provider keys, Resend/FCM
  keys, R2 credentials, and encryption keys **server-side only**.
- **MUST** use environment variables or the approved secret store; never hard-code values.
- **MUST** use `.env.example` with placeholder names only; never commit `.env` files.
- **MUST** treat customer test cookies/Bearer tokens as encrypted secrets; never return them raw from
  an API, render them unmasked, or log them.
- **MUST** generate GitHub installation tokens on demand; never persist them.
- **MUST** redact secrets/PII in tests, fixtures, screenshots, and error messages.
- **MUST** rotate any secret that may have leaked and report the incident immediately.

---

## 5. Authorization and server-side validation

- **MUST** validate and authorize every sensitive action **server-side** (FastAPI), even if the UI
  hides the action.
- **MUST** verify workspace ownership on every request that touches workspace data.
- **MUST** include `workspace_id` explicitly in every service-role query; never rely on RLS alone for
  privileged paths.
- **MUST** keep RLS enabled and forced on every tenant table; new tables require policies and tests
  in the same change.
- **MUST** use the Supabase anon key + RLS for client-direct access; the service role is server-only.
- **MUST** validate all input with Pydantic schemas (API) and schema validation (web/mobile).
- **MUST** enforce quotas, plan limits, and scan concurrency server-side.
- **MUST** verify GitHub webhook HMAC (`X-Hub-Signature-256`) before parsing; enforce idempotency.
- **MUST NOT** trust client-supplied `workspace_id`, `user_id`, roles, scan status, or quota values.
- **MUST NOT** add an endpoint that bypasses the egress guard or the PII sanitizer.

---

## 6. Scanning safety (product-critical)

- **MUST** route every outbound scan request through the egress guard:
  - exact host match with the verified domain,
  - pre-connect DNS resolution and private/internal IP rejection (SSRF, DNS rebinding),
  - cross-domain redirect blocking,
  - rate limiting at the HTTP client level.
- **MUST** enforce Safe Mode on Production: non-mutating requests only (GET/HEAD/OPTIONS), ≤ 2 req/s,
  200–300 requests, explicit consent.
- **MUST** enforce Deep Mode on Staging: ≤ 10 req/s, up to 600 requests, non-destructive active checks.
- **MUST** refuse destructive actions: `DROP`, `DELETE`, `UPDATE`, `TRUNCATE`, `ALTER`, DoS/stress,
  brute-force/credential stuffing, malicious uploads, reverse shells, destructive RCE, DB dumps, and
  customer-data exfiltration.
- **MUST** stop gracefully at hard caps (15 minutes, 100K tokens / 25 LLM calls, request caps) and
  mark **Partial coverage** instead of failing silently.
- **MUST NOT** scan outside the verified domain, even if the target content or an LLM output asks for
  it.
- **MUST NOT** disable or weaken the egress guard, sanitizer, or hard refusals for tests or demos.

---

## 7. Privacy and data handling

- **MUST** run the deterministic sanitizer before storing evidence and before sending anything to an
  LLM.
- **MUST** redact Authorization/Cookie/Set-Cookie/X-API-Key headers, JWTs, card numbers (Luhn),
  emails, phone numbers, and API keys (`sk_`, `ghp_`, `AKIA`).
- **MUST NOT** store raw HTTP traffic; only sanitized PoCs for confirmed findings, coverage stats, and
  scan events.
- **MUST NOT** read, upload, or exfiltrate `.env` files or customer secrets from repositories.
- **MUST NOT** perform DB dumps or pull real customer data to prove a finding.
- **MUST** honor retention rules: scan events 14 days; findings/reports 90 days (or last 10 scans per
  domain in beta); audit logs 12 months; webhook deliveries 7 days.
- **MUST** delete domain data (findings, evidence, test cookies, PDFs) on domain deletion, retaining
  only the minimal audit proof.
- **MUST** anonymize audit records on GDPR deletion requests while preserving the legal minimum.

---

## 8. AI/LLM rules

- **MUST** treat all target responses as untrusted data; wrap/tag them and never place them in system
  prompts.
- **MUST** require structured JSON output (Pydantic schema); never allow free-form URLs, hosts, or tool
  selection.
- **MUST** use LiteLLM routing and only providers approved in `plan.md` §11.3 (no free tier that
  permits training on customer data).
- **MUST** respect hard caps and log tokens/calls/cost per scan.
- **MUST** keep the deterministic/LLM split measurable; do not move deterministic work into prompts.
- **MUST NOT** add a provider, model, or prompt that can bypass the egress guard or sanitizer.
- **MUST NOT** send entire repositories, `.env` files, or PII to an LLM.

---

## 9. Code quality and dependencies

- **MUST** follow existing structure, naming, and style.
- **MUST** use TypeScript strict mode for web; typed Python (type hints) for services.
- **MUST** keep SQL migrations append-only and backward-compatible; never edit an applied migration.
- **MUST** back up the database before any schema migration (see `plan.md` §18).
- **MUST** pin dependency versions and update lockfiles; justify every new dependency in the PR.
- **MUST NOT** invent packages, scripts, or APIs; verify they exist and are maintained.
- **MUST NOT** add telemetry or third-party scripts that capture PII.
- **MUST** handle errors explicitly; no swallowed exceptions or silent fallbacks on security paths.
- **MUST** use the shared design tokens in `design.md`; no raw hex values in components.

---

## 10. Testing and verification

- **MUST** write or update tests for every changed behavior.
- **MUST** run available lint, typecheck, and test commands before declaring work complete.
- **MUST** add/extend:
  - unit tests for pure logic (fingerprint, score, sanitizer, parsers),
  - integration tests for API/DB/RLS/queue/webhooks,
  - Playwright E2E for changed user journeys,
  - security tests for guardrails, sanitizer, RLS, HMAC,
  - golden/patch benchmark tests for agent behavior changes.
- **MUST** keep the security suite at 100% pass; never skip or xfail security tests.
- **MUST** update Playwright selectors via `data-testid` from `design.md` §13.4.
- **MUST** report exact commands run and their results.
- **MUST NOT** mark a task complete if required checks fail or were not run.
- **MUST NOT** weaken assertions, delete tests, or skip checks to make CI green.

---

## 11. Commits and pull requests

- **MUST** use Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`,
  `security:`.
- **MUST** keep commits small and reversible; one logical change per commit.
- **MUST** write a PR description with: what changed, why, risk, test evidence, screenshots (UI),
  rollback plan, and remaining unverified items.
- **MUST** link the relevant milestone/task.
- **MUST NOT** force-push to protected branches (`main`, release branches).
- **MUST NOT** enable auto-merge; human review is required.
- **MUST NOT** commit generated secrets, build artifacts, or local `.env` files.
- **MUST** respect CODEOWNERS for security-sensitive paths.

---

## 12. Deployment and production safety

- **MUST NOT** deploy, delete data, run destructive migrations, rotate production secrets, or alter
  production infrastructure without explicit human approval.
- **MUST** validate on staging first; production deploys require a release tag and manual approval.
- **MUST** take an encrypted backup before migrations.
- **MUST** provide a rollback plan for every deploy.
- **MUST** verify health checks after deploy and report the result.
- **MUST** use the kill switch if a scan causes harm; document the incident.
- **MUST NOT** run destructive commands (`docker compose down -v`, `DROP TABLE`, volume pruning) on
  any shared environment (staging or production).
- **MUST NOT** expose new ports or bypass Cloudflare/origin restrictions.

---

## 13. Change report (required for every task)

Every completed task **MUST** include:

```markdown
## Change report
- Scope: <milestone/task>
- Files changed: <list>
- What changed: <concise>
- Tests run: <commands + results>
- What remains unverified: <explicit list or "none">
- Risks/rollback: <notes>
- Follow-ups: <TBDs or "none">
```

Never omit "what remains unverified." If nothing was tested, say so explicitly.

---

## 14. Prohibited actions (hard stops)

- Exposing secrets/service-role keys to browser, mobile, GitHub, logs, or screenshots.
- Bypassing or weakening the egress guard, sanitizer, RLS, HMAC verification, or hard refusals.
- Adding auto-merge or auto-deploy for customer PRs.
- Scanning a domain without verified ownership and recorded consent.
- Storing raw HTTP traffic or customer PII.
- Destructive SQL/DoS/brute-force/RCE/data-exfiltration payloads.
- Editing applied migrations or audit logs.
- Deploying to production or deleting data without approval.
- Inventing facts, dependencies, model capabilities, or "verified" claims.
- Committing `.env`, credentials, or customer data.
- Adding out-of-scope features (payments, multi-user, iOS, etc.) without approval.

---

## 15. Definition of Done

A task is done only when:

- [ ] It is within the approved scope/milestone.
- [ ] Code follows `design.md` and `plan.md`.
- [ ] Server-side validation/authorization is in place.
- [ ] No secrets/PII are exposed.
- [ ] Tests are added/updated and pass.
- [ ] Lint/typecheck pass.
- [ ] Security-relevant tests pass (RLS, egress, sanitizer, HMAC).
- [ ] UI states (empty/loading/error/success) are implemented.
- [ ] Accessibility checks pass for UI changes.
- [ ] The change report is complete, including unverified items.
- [ ] Rollback is possible.

---

## 16. When to stop and ask

Stop and request human input when:

- The task conflicts with `design.md`, `plan.md`, or the approved brief.
- A new dependency, service, provider, or infrastructure change is required.
- A database migration could be destructive or non-backward-compatible.
- A security control would need to be weakened or bypassed.
- Production deploy, data deletion, or secret rotation is involved.
- A TBD blocks implementation and guessing would create a project fact.
- Test results are ambiguous or a required check cannot run.

Do not guess. Do not "fix" by disabling. Do not proceed on production without approval.

---

## 17. Repository map (orientation)

```
apps/web            Next.js web app
apps/mobile         Flutter Android owner companion
services/api        FastAPI API
services/worker     Python worker + LangGraph agents
packages/shared     Shared schemas/types
supabase            Migrations, RLS policies, RLS tests
tests/e2e           Playwright
tests/security      SSRF/egress, canary, prompt injection, HMAC
tests/golden        Golden suite + patch benchmark
fixtures            Vulnerable apps + seeds
infra               Dockerfiles, platform configs, scripts
.github/workflows   CI, staging/prod deploy, backups
design.md           UX/UI source of truth
plan.md             Technical source of truth
AGENTS.md           This file
```

---

## 18. Environment notes

- Hosting: **$0 free tiers** — Vercel Hobby (web) + Railway/Render/Oracle Cloud Free (API/worker) +
  **Cloudflare DNS/TLS/WAF**. No VPS in v1; a commercial hosting upgrade is required before v2
  payments.
- Data: **Supabase EU Frankfurt (eu-central-1)**; reports in Supabase Storage; backups/audit JSONL
  in **Cloudflare R2**.
- Environments: `dev` (local Docker + Supabase local), `staging`, `prod` (separate Supabase projects,
  separate platform environments and env vars).
- CI/CD: GitHub Actions + platform builds (Vercel/Railway/Render/Oracle); production deploys from
  release tags with manual approval.
- Mobile: Android only; iOS is permanently out of scope.
- All values not specified here are **TBD** — see `plan.md` §22. Never invent them.
