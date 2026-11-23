# design.md — Mirsad v1 Beta

| Field | Value |
|---|---|
| Status | Approved for implementation planning — derived from Product Brief v1.0 |
| Product | Mirsad (مرصاد) |
| Scope | v1 Beta: web app (6 pages) + Android owner companion app + PDF report |
| Last updated | 2026-11-22 |
| Source of truth | Approved Product Brief v1.0 + the 100-question decision log |
| Companion docs | `plan.md` (technical plan), `AGENTS.md` (coding-agent rules) |

> This document is the UX/UI source of truth. If a detail here conflicts with the approved
> Product Brief, the Brief wins. If a detail conflicts with `plan.md`, this document wins for
> UX behavior and `plan.md` wins for implementation constraints. Anything marked **TBD** is an
> open decision and must not be invented during implementation.

---

## 1. Product experience goals

### 1.1 What the experience must achieve

1. **Evidence over assurance.** The product never says "you are 100% secure". It shows what was
   tested, what was found, what was fixed, and what was verified.
2. **Calm clarity under pressure.** A developer opening the dashboard after an alert should know
   in under 10 seconds: what is critical, what needs review, and what is already handled.
3. **Developer-native.** The product lives where developers work: GitHub PRs, diffs, CI status,
   commit context. The web app is a control room, not a replacement for GitHub.
4. **Honest coverage.** "No findings" is never presented as proof of safety. Every scan ships with
   a Coverage Receipt that states scope, attempts, and blind spots.
5. **Safe by visible design.** Environment (Staging/Production), Safe Mode, authorized domain,
   and human approval gates are visible at the moment of action — not buried in settings.
6. **Fast first value.** Live logs appear in under 30 seconds; the first confirmed finding and PR
   should land within 10–15 minutes. Waiting must feel observable, not opaque.
7. **Trust through restraint.** No auto-merge, no auto-deploy, no destructive tests. The UI makes
   the human gate explicit and predictable.

### 1.2 Experience principles

| Principle | What it means in the UI |
|---|---|
| Show the loop | Every issue displays its lifecycle: Detected → PR Opened → Merged → Verified Fixed |
| One primary action per screen | e.g., Dashboard: review critical issues; Issue: review the PR; Domain: run scan |
| Progressive disclosure | Summary first; raw HTTP, payloads, and diffs behind tabs/toggles |
| No color-only meaning | Every status = color + icon + explicit text |
| Never bluff | Unknown or incomplete coverage is labeled, not hidden |
| Reversible by default | Destructive actions require typed confirmation; PRs are isolated and revertible |
| Quiet by default | Motion and color are used for meaning, not decoration |

### 1.3 Non-goals for v1 UX

- No asset discovery or attack-surface inventory UI.
- No in-app code editor or merge button.
- No shareable public report links.
- No multi-user seats, roles, or team management screens.
- No Arabic/RTL UI (v2).
- No iOS app (permanently out of scope).
- No 24/7 offensive monitoring visualization; "Live" means live logs of a running scan.

---

## 2. Audience and contexts of use

### 2.1 Primary users

| Persona | Context | Needs |
|---|---|---|
| **Developer / Tech Lead** (daily user) | Laptop, GitHub open in another tab, during a deploy window | See verified issues, review PRs, understand evidence, re-verify after deploy |
| **CTO / Founder** (buyer, occasional) | Weekly review, investor/security questions | Posture trend, coverage honesty, PDF report, confidence that nothing is auto-merged |
| **Workspace Owner** (v1 account) | Desktop + Android phone | Manage domains, GitHub connection, alerts, quota |
| **Security reviewer** (external, via PDF only) | Offline review | Sanitized evidence, timeline, verification result, no customer PII |

### 2.2 Contexts

- **Onboarding:** during a workday, likely interrupted; every step must be resumable.
- **Alert response:** on phone or laptop; the first screen must answer "is this real and what do I do?"
- **Deploy verification:** immediately after a merge/deploy; the re-attack state must be obvious.
- **Weekly review:** trend, open issues, PR status, coverage.
- **Incident:** calm, explicit states; no ambiguous spinners.

### 2.3 Language and direction

- v1 UI language: **English only**, `lang="en"`, `dir="ltr"`.
- Arabic/RTL is a v2 concern; do not hard-code layouts that cannot be mirrored later.
- All timestamps: display in the user's local timezone, with UTC available in technical logs.
- Technical identifiers (endpoints, headers, code) are always LTR and monospace.

---

## 3. Brand and visual identity

### 3.1 Brand personality

**Precise, calm, transparent, developer-grade.** Mirsad is the quiet senior security engineer in
the room — not a fear-selling alarm system. It states facts, shows evidence, and never exaggerates.

**Voice:** direct, specific, non-judgmental. Short sentences. No hype. No "military" metaphors.
No blame ("your code is insecure"); instead: "A confirmed SQL injection was found at
`POST /api/login`; a fix PR is ready for review."

### 3.2 Logo and wordmark

- Wordmark: **Mirsad** set in Syne (700), Light Lavender on Dark Navy.
- Logo symbol: **TBD** (no asset approved yet). Until approved, use the wordmark only.
- Clear space: at least the height of the "M" on all sides.
- Do not recolor the logo with Neon Cyan or place it on Deep Purple without contrast review.

### 3.3 Color system

#### Approved palette (non-negotiable)

| Token | Hex | Role | Rules |
|---|---|---|---|
| `--color-bg` | `#0F1523` | App background (Dark Navy) | Primary canvas for web and mobile |
| `--color-secondary` | `#4A289A` | Deep Purple: button backgrounds, badges, gradients | **Never** used as direct text on `#0F1523` |
| `--color-accent` | `#44ECF1` | Neon Cyan: links, focus rings, active states, key data | Never used for long body text; never as text on white PDF |
| `--color-text` | `#E8E8FA` | Primary text (Light Lavender) | Default text on dark surfaces |

#### Derived surface tokens (documented derivation, not new brand colors)

These are computed from the approved palette using transparency over Dark Navy. They must be
implemented as tokens, not hand-picked hex values.

| Token | Derivation | Usage |
|---|---|---|
| `--color-surface-1` | `color-mix(in srgb, #E8E8FA 4%, #0F1523)` | Cards, panels |
| `--color-surface-2` | `color-mix(in srgb, #E8E8FA 7%, #0F1523)` | Hover, raised rows |
| `--color-border` | `color-mix(in srgb, #E8E8FA 14%, transparent)` | Default borders |
| `--color-border-strong` | `color-mix(in srgb, #E8E8FA 24%, transparent)` | Focused/selected borders |
| `--color-text-muted` | `color-mix(in srgb, #E8E8FA 64%, #0F1523)` | Secondary text |
| `--color-text-faint` | `color-mix(in srgb, #E8E8FA 42%, #0F1523)` | Captions, timestamps |

#### Semantic status colors — **PROPOSED, TBD sign-off**

The approved palette does not define severity/success/warning colors. The following is a
**proposal for design sign-off**, not an approved fact. Until approved, implement semantic roles
with placeholder tokens and never rely on color alone (icon + text are mandatory).

| Role | Proposed hex | Notes |
|---|---|---|
| Critical | `#FF6B81` | Must meet ≥ 4.5:1 on `#0F1523`; pair with filled octagon icon |
| High | `#FF9F43` | Pair with triangle icon |
| Medium | `#FFD166` | Pair with diamond icon |
| Low | `#7BD88F` | Pair with circle icon |
| Success / Verified | `#3DDC97` | Pair with check icon |
| Warning / Blocked | `#FFB020` | Pair with alert icon |
| Info / Neutral | `#8FB8FF` | Pair with info icon |

**Rules:** every status must have (1) color, (2) icon, (3) explicit text label. Do not use red/green
as the only differentiator. Validate all pairs with a contrast checker before sign-off.

#### Color usage examples

- Primary button: Deep Purple background, Light Lavender text, Neon Cyan focus ring.
- Destructive button: transparent background, critical border/text, icon + label.
- Active nav item: Neon Cyan left indicator + Light Lavender text; not a full cyan background.
- Charts: Neon Cyan for the primary trend; muted lavender for gridlines; severity colors only for
  severity-coded series, always with labels.

### 3.4 Typography

| Role | Typeface | Weights | Notes |
|---|---|---|---|
| Brand / headings | **Syne** | 600, 700 | H1–H3 and brand wordmark only |
| Body / UI | **Inter** | 400, 500, 600 | Fixed v1 choice; optimized for dense tables and log-adjacent UI |
| Code / logs / diffs | **JetBrains Mono** | 400, 500 | Endpoints, payloads, headers, diffs, raw logs |

**Type scale (desktop):**

| Token | Size / line-height | Usage |
|---|---|---|
| `text-xs` | 12 / 16 | Captions, timestamps, badges |
| `text-sm` | 14 / 20 | Tables, secondary UI |
| `text-base` | 16 / 24 | Body |
| `text-lg` | 18 / 28 | Card titles |
| `text-xl` | 20 / 28 | Section titles |
| `text-2xl` | 24 / 32 | Page subtitles |
| `text-3xl` | 30 / 36 | Page titles |
| `text-4xl` | 36 / 44 | Marketing/empty-state headlines |
| `text-5xl` | 48 / 56 | Score display (optional) |

Use `font-variant-numeric: tabular-nums` for scores, counters, and tables.

### 3.5 Iconography and imagery

- Icons: Lucide (shadcn/ui default), 1.5px stroke, 16/20/24px sizes.
- No stock photography, no hacker/hoodie imagery, no skulls.
- Illustrations: none in v1; empty states use icon + copy, not cartoons.
- Charts: minimal gridlines, no 3D, no gradients as data encoding.

### 3.6 Motion

| Token | Duration | Usage |
|---|---|---|
| `motion-fast` | 120ms | Hover, focus |
| `motion-base` | 180ms | Tabs, drawers, toasts |
| `motion-slow` | 280ms | Page transitions, chart reveal |

- Easing: `cubic-bezier(0.2, 0, 0, 1)`.
- Respect `prefers-reduced-motion`: disable non-essential animation; live counters may update
  without transitions.
- Never animate critical status changes in a way that could be missed; announce via live region.

### 3.7 Dark-first and print

- The product is **dark-first** for web and mobile.
- The PDF report uses a **light print theme**: white background, Dark Navy and Deep Purple for
  headings/headers, Light Lavender or white for text on dark header bars.
- **Never** print Neon Cyan text on white. Use cyan only as a thin accent rule or chart highlight.

---

## 4. Information architecture

### 4.1 Web sitemap

```
/sign-in
/onboarding
/dashboard
/domains
  /domains/new
  /domains/[domainId]
/pentests
  /pentests/[scanId]
/issues
  /issues/[findingId]
/pr-reviews
  /pr-reviews/[patchId]
/settings
  ?tab=profile | github | notifications | workspace | danger
```

### 4.2 Global navigation

**Desktop (≥ 1024px):**

- Fixed left sidebar, 264px:
  - Wordmark at top.
  - **Domain selector** directly below the wordmark (workspace-wide context).
  - Primary nav: Dashboard, Domains, Pentests, Issues, PR Reviews, Settings.
  - Bottom: quota meter (Beta), user menu (GitHub avatar, sign out).
- No heavy top bar. Each page has a light page header inside the content area with:
  - Title + optional subtitle.
  - Primary action (e.g., **Run scan**) and secondary actions.
- Content max width 1440px; page padding 24px (mobile) / 32px (desktop).

**Tablet/mobile (< 1024px):**

- Sidebar becomes a collapsible drawer triggered by a menu button in the page header.
- Domain selector moves into the drawer and a compact selector appears in the page header.
- Reading pages (Dashboard, Issues, Scan detail) are fully responsive; code diffs stack.

### 4.3 Navigation rules

- The domain selector filters Dashboard, Pentests, Issues, and PR Reviews. Domains and Settings are
  workspace-scoped.
- Selecting "All domains" is allowed on Dashboard/Issues; scan actions always require one domain.
- Deep links must survive refresh and sign-in (redirect back to the intended route).
- The active nav item uses a Neon Cyan left indicator + Light Lavender text.
- The browser back button must behave predictably: filters are URL query parameters where practical.

### 4.4 Mobile app sitemap (Android owner companion)

```
Login (GitHub OAuth PKCE)
Home (Domains + Posture Score)
Issues (list → detail + PR status)
Activity (Notifications + Live Scan Status)
```

- Read-only except: sign in/out, register/remove device token, mark notification read.
- No scan creation, no domain management, no settings beyond notifications/sign-out.
- Tapping an issue opens a read-only detail; "Open on GitHub" opens the PR in the browser.
- Tapping a live scan shows the phase timeline and counters, not raw logs (raw logs are web-only).

---

## 5. User journeys

### J1 — First-run onboarding (new workspace)

**Goal:** from sign-in to first scan in under 5 minutes of active work.

1. **Sign in** with GitHub OAuth. First-time users land on `/onboarding`.
2. **Add domain:** enter domain (e.g., `app.example.com`), choose environment (Staging/Production).
3. **Verify ownership:** choose DNS TXT or file upload (`/.well-known/verify.txt`). UI shows exact
   record/file content with copy buttons and a "Check verification" action.
4. **Legal consent:** read and check the Rules of Engagement (required). Consent is recorded with
   version, timestamp, and IP.
5. **Optional repo link:** "Connect GitHub" (GitHub App). Can be skipped; scan-only mode is fully
   supported.
6. **First scan:** run scan. Live logs appear within 30 seconds.
7. **First value:** a confirmed issue with sanitized PoC; if repo is linked, a PR link appears.

**Failure branches:** verification fails (reason + retry + alternative method); repo connection
fails (continue scan-only); WAF blocks scan (banner + staging suggestion); quota reached (blocked
state with reset date).

**Success state:** domain verified, first scan completed (or partial with Coverage Receipt), and a
clear next action.

### J2 — Scan-only (Black Box)

1. Owner adds and verifies a domain, skips repo linking.
2. Runs a scan; Red agent performs recon and deterministic checks within Safe/Deep mode limits.
3. Issues appear with sanitized evidence; each issue shows a CTA: "Connect GitHub to fix
   automatically."
4. PDF report is available; Coverage Receipt explains scope and blind spots.

**Emotional goal:** low commitment, high transparency. The user can evaluate accuracy before granting
code access.

### J3 — Grey-box loop (repo linked)

1. Owner links a GitHub repo via the GitHub App (least privilege).
2. Red agent uses code-informed recon (routes/controllers) plus black-box probing.
3. Confirmed findings appear; Blue agent opens one PR per finding (or related findings in the same
   file) with a minimal diff, explanation, and testing instructions.
4. Developer reviews on GitHub, CI runs, and the developer merges (or requests changes/closes).
5. On merge + deploy, Mirsad re-attacks (automatic via `deployment_status` or manual "Re-verify
   Now"). The issue becomes **Verified Fixed** only after the re-attack succeeds.
6. Score updates only on verified fixes; the PDF records before/after evidence.

### J4 — PR outcomes

| GitHub action | Mirsad behavior | UI state |
|---|---|---|
| **Merge** | Trigger re-attack (webhook or manual) | `Merged — Waiting for Deploy` → `Re-verifying` → `Verified Fixed` / `Still Vulnerable` |
| **Request changes** | No infinite comment loop in v1; issue stays `Patch Needs Review`; "Regenerate Fix" available with an optional note | `Patch Needs Review` |
| **Close (rejected)** | Issue stays open; owner can mark `False Positive` or `Won't Fix`; Blue does not reopen automatically (anti-spam) | `Open` / `False Positive` / `Won't Fix` |
| **CI fails** | Patch marked `CI Failed`; "Regenerate Fix" can include the CI error log as input | `CI Failed` |
| **Branch conflict** | Patch marked `Needs Rebase`; no force push; regenerate or manual resolution | `Needs Rebase` |

### J5 — Re-attack and verification

- Automatic trigger: `deployment_status` webhook (successful deployment).
- Fallback: after PR merge, if no deployment event arrives within 10 minutes, the issue shows
  `Merged — Waiting for Deploy` with a **Re-verify Now** button and a notification.
- The re-attack is focused on the specific finding (not a full scan) to save time and tokens.
- Evidence is appended (not replaced) so the PDF can show before/after.
- If still vulnerable: `Still Vulnerable`, issue reopens, and the Blue agent may propose a new patch
  only after explicit user action.

### J6 — Zero findings (the honesty journey)

- The scan completes with no confirmed issues.
- The UI **never** says "100% secure". It shows:
  - Headline: **"No vulnerabilities detected within tested scope."**
  - **Coverage Receipt:** endpoints/pages tested, vulnerability classes attempted and attempt counts,
    what could not be tested and why (e.g., "4 pages require login — add a test token", "WAF blocked
    3 paths").
  - CTAs: "Add optional test cookie/auth header" and "Configure scheduled scans".
- If coverage is incomplete (WAF, timeout, partial), the state is **Unscored / Incomplete Scan**, not
  100.

### J7 — WAF / Cloudflare block

1. Scan detects 403/challenge responses.
2. Orange banner: "WAF/Cloudflare blocked the scanner (403/Challenge)." Explains why this is not
   evidence of safety.
3. Actions: allowlist Mirsad's scanner IP/user-agent, or **Switch to Staging**.
4. The scan is marked `Blocked` or `Partial`, with affected paths listed in the Coverage Receipt.

### J8 — Verification failure

- Failure reason is specific: DNS TXT not found, TXT not propagated yet, file returned 404, file
  content mismatch, or domain unreachable.
- Actions: **Retry**, **Try alternative method**, and a documentation link.
- No generic "Something went wrong".

### J9 — Quota and plan limits (Beta)

- Beta: 2 domains, 5 scans/month total per workspace, 1 owner.
- At 80% usage: inline warning in the quota meter.
- At 100%: automated scans pause; dashboard and reports remain readable. Manual scan button is
  disabled with a clear explanation and reset date. No surprise charges (payments are v2).

### J10 — Deletion and disconnection

- **Delete domain:** type the domain name to confirm; any running scan stops immediately; findings,
  evidence, test cookies, and PDFs for that domain are deleted. Audit log retains minimal legal proof.
- **Disconnect GitHub:** revoke tokens, remove webhooks, pause the Blue agent. Existing PRs remain on
  GitHub; historical data remains readable in Mirsad.
- **Delete workspace/account:** type `DELETE`; revoke tokens; delete temporary code, findings, and
  reports; anonymize audit records per the retention policy.

---

## 6. Screen specifications

> All screens are dark theme, English/LTR, keyboard accessible, and responsive per §9.
> Data-testid conventions are defined in §13.4.

### 6.1 Sign in (`/sign-in`)

**Purpose:** authenticate with GitHub and route to onboarding or dashboard.

**Layout:** centered card on Dark Navy; wordmark; one-line value statement; GitHub OAuth button;
small print linking to Terms and Privacy.

**Components:** `OAuthButton`, `Alert` (for auth errors), `Spinner`.

**States:**
- Default: "Continue with GitHub".
- Loading: button disabled, spinner, "Redirecting to GitHub…".
- Error: "GitHub sign-in was cancelled or failed." + retry; do not reveal internal details.
- Session expired: inline message + re-auth.

**Acceptance:** OAuth is the only sign-in method; no email/password fields; keyboard focus starts on
the button; error is announced to screen readers.

### 6.2 Onboarding (`/onboarding`)

**Purpose:** get a new workspace to its first scan.

**Layout:** 3-step stepper (Add domain → Verify → First scan) with a persistent progress indicator.
Each step is a card with a single primary action. Repo linking is an optional step between Verify
and Scan.

**Step 1 — Add domain:**
- Domain input with normalization (lowercase, strip protocol/path).
- Environment radio: Staging (recommended, Deep Mode) / Production (Safe Mode; explicit consent).
- Helper: "Staging lets Mirsad test more deeply without touching production."

**Step 2 — Verify ownership:**
- Method tabs: DNS TXT | File upload.
- DNS: name, type, value (copyable), TTL guidance, "Check verification" button; polling state.
- File: exact path `/.well-known/verify.txt`, file content (copy/download), "Check verification".
- Legal consent checkbox (required) with link to Rules of Engagement; version shown.
- Failure: specific reason + Retry + Try alternative method.

**Step 3 — Connect GitHub (optional):**
- GitHub App install button; explain least-privilege permissions; "Skip for now" is prominent.
- If connected: repo selector (searchable), default branch display.

**Step 4 — First scan:**
- Summary card (domain, environment, repo or scan-only).
- Primary: **Run first scan**; secondary: "Go to dashboard".
- After start: redirect to scan detail with live logs.

**Empty/edge states:** domain already claimed by another workspace (error); domain invalid; consent
not checked (button disabled with explanation).

### 6.3 Dashboard (`/dashboard`)

**Purpose:** the 10-second answer to "what is my security state right now?"

**Layout (top to bottom):**
1. Page header: "Dashboard", domain selector context, **Run scan** (disabled if no verified domain).
2. Four clickable KPI cards:
   - **Security Score** + delta since last scan + coverage context (e.g., "88/100 · Unauthenticated ·
     12 endpoints"). If unscored: "Unscored" with reason.
   - **Open Critical / High Issues** (count, with severity split).
   - **Pending PRs** (count; includes CI failed/needs rebase).
   - **Last Scan Status & Coverage** (status pill + timestamp + coverage %).
3. Banner area (conditional):
   - Live scan running: cyan-tinted banner with phase + elapsed time + "View live logs".
   - Open critical issue: critical banner with count + "Review critical issues".
   - WAF blocked/partial: warning banner.
4. **Top open issues table:** severity, title, endpoint, status, PR status, last seen; sorted by
   severity then recency. Row click → issue detail.
5. **Posture trend chart:** score over the last N scans, with coverage annotations; empty state if
   fewer than 2 scans.

**States:**
- No domains: onboarding empty state with "Add your first domain".
- No scans yet: "Run your first scan" card.
- All clear: score + "No vulnerabilities detected within tested scope" + Coverage Receipt link.
- Loading: skeletons for cards/table/chart; no layout shift.
- Error: retryable panel with request ID.

### 6.4 Domains list (`/domains`)

**Purpose:** manage domains, environments, verification, and repo links.

**Layout:** page header + "Add domain"; table/cards with columns:
Domain, Environment, Verification, Repo, Last scan, Score, Next scan, Actions (overflow menu).

**Row actions:** View details, Run scan, Re-verify, Copy verification record, Delete (danger).

**States:** empty (onboarding CTA), loading skeleton, error, verified/unverified badges, disconnected
repo badge, quota warning.

### 6.5 Add domain (`/domains/new`)

Reuses the onboarding steps 1–2 and optional repo step. On success, routes to domain detail with a
"Run first scan" CTA. Includes a "What Mirsad will and will not do" safety summary and the legal
consent gate.

### 6.6 Domain detail (`/domains/[domainId]`)

**Purpose:** single-domain control room.

**Header:** domain name, environment badge, verification badge, score, **Run scan**, overflow menu.
**Tabs:**
- **Overview:** last scan summary, open issues by severity, repo status, coverage receipt link,
  next scheduled scan.
- **Scans:** history table (same as Pentests, filtered).
- **Issues:** filtered issues.
- **Auth config:** optional test cookie/Bearer token; masked input; "Clear/Update"; warning that
  credentials are encrypted and only used for scans; 401 detection notice.
- **Repo:** connection status, repo name, default branch, disconnect action.
- **Danger zone:** delete domain with typed confirmation.

**States:** unverified (scan disabled with reason), verification pending, WAF blocked, repo
disconnected, quota reached.

### 6.7 Pentests (`/pentests`)

**Purpose:** scan history and live scan entry point.

**Layout:** table/cards: date, trigger (manual/push/deploy/schedule/re-verify), status, duration,
coverage, findings (confirmed/suspected), score delta. Filters: domain, status, trigger, date range.

**States:** empty ("No scans yet"), running (live badge), partial, blocked, failed, unreachable.

### 6.8 Scan detail / Live logs (`/pentests/[scanId]`)

**Purpose:** observe a running scan and review a completed episode.

**Layout:**
- Header: scan status pill, domain, environment, trigger, started time, elapsed, **Cancel scan**
  (running only).
- **Phase Timeline:** Verification & Recon → Probing Endpoints → Confirming Exploits → Blue Agent
  Patching → Opening PR. Each phase shows state (pending/running/done/skipped/failed) and a one-line
  status.
- **Live counters:** endpoints tested, tests run, findings found, requests used, tokens used (cost
  telemetry visible to owner).
- **Toggle:** "Show raw technical logs" (monospace, virtualized, auto-scroll with pause on hover).
- **Results summary:** confirmed/suspected counts, score delta, coverage receipt, report download
  (when ready), issues list.
- **Waiting UX:** "You can close this page — we'll notify you by email/push when the scan finishes."

**States:** queued (position + fair-scheduling note), running, completed, partial (reason), blocked
(WAF), unreachable, failed (error code + retry), cancelled.

### 6.9 Issues (`/issues`)

**Purpose:** triage confirmed and suspected findings.

**Layout:** page header + filters (status, severity, type, endpoint, domain). Default sort: severity
(Critical → Low), then last seen. Confirmed issues first; suspected findings in a separate
"Informational" section (not scored, no auto-PR).

**Columns/cards:** severity badge, title, endpoint/method, status, PR status, last seen, actions.

**States:** empty (coverage receipt + CTAs), loading, error, filtered-empty (clear filters).

### 6.10 Issue detail (`/issues/[findingId]`)

**Purpose:** understand, trust, and act on a finding.

**Layout:**
- Header: severity + title, endpoint/method, confidence (Confirmed/Suspected), status pill, last
  seen, fingerprint (copyable, secondary).
- **Lifecycle stepper:** Detected → PR Opened → Merged → Verified Fixed (with current state and
  timestamps).
- **Summary:** impact, affected parameter, OWASP category, description.
- **Evidence tabs (progressive disclosure):**
  - **Proof of Concept:** sanitized, reproducible steps.
  - **Sanitized HTTP:** request/response with redactions; copyable.
  - **Patch & Diff:** diff, PR link, CI status, explanation.
- **Actions:** Open PR on GitHub, Regenerate Fix (with optional note), Re-verify Now, Mark False
  Positive, Mark Won't Fix. Destructive/terminal actions require confirmation.
- **Verification history:** append-only attempts with before/after result.
- **Suspected findings:** show "Informational — not scored; no automatic PR" and a CTA to request a
  deeper scan (if eligible).

### 6.11 PR Reviews (`/pr-reviews`)

**Purpose:** track the status of Mirsad-authored PRs without leaving the control room.

**Layout:** table/cards: PR title, issue, repo, branch, status (PR Open, CI Failed, Changes
Requested, Merged, Waiting for Deploy, Needs Rebase, Closed), CI status, updated time, PR link.

**Rules:** review and merge happen on GitHub; Mirsad never auto-merges. The page is a status mirror.

### 6.12 PR Review detail (`/pr-reviews/[patchId]`)

**Layout:** PR summary, linked issue, diff viewer (stacked on mobile), CI checks, PR link, verification
status, actions (Regenerate Fix, Re-verify Now). If CI failed: show failure summary + link to logs.

### 6.13 Settings (`/settings`)

Tabs:
- **Profile:** GitHub identity, email (read-only from GitHub), sign out.
- **GitHub:** installation status, connected repos, permissions summary, disconnect (danger).
- **Notifications:** email and push toggles (critical/high findings, PR ready, scan failed/blocked);
  device list with remove.
- **Workspace:** name, plan/usage (Beta limits), audit retention notice, export audit log (owner).
- **Danger zone:** delete workspace with typed `DELETE`.

### 6.14 Mobile app (Android owner companion)

**S1 — Login:** GitHub OAuth via PKCE + deep link; error states; no email/password.
**S2 — Home:** domain cards with environment, verification, score, last scan, open critical/high
count; pull-to-refresh; tap → domain summary (read-only).
**S3 — Issues:** list (severity sort, filters by status/domain), detail with summary + PR status +
"Open on GitHub"; no raw logs.
**S4 — Activity:** notifications log + live scan status (phase, counters, ETA); mark read; tap to
deep-link into the web app for details.

**Push notification content:** no sensitive details in the notification body; e.g., "Mirsad: a
Critical issue needs review on app.example.com" → opens the app. No payloads, no customer data.

### 6.15 PDF report (visual specification)

- **Theme:** light print; white background; Dark Navy and Deep Purple headings/headers; body text
  dark gray/navy; no Neon Cyan text on white.
- **Length:** 4–8 pages, focused.
- **Structure:**
  1. Cover: domain, environment, date, ownership proof reference, report ID.
  2. Executive summary (1 page): score before/after, confirmed issue counts, verification outcome,
     Coverage Receipt summary.
  3. Episode timeline: phases, timestamps, triggers.
  4. Findings: each confirmed issue with OWASP category, severity, sanitized PoC, patch diff, PR
     link, final verification status (Verified Fixed / Still Vulnerable).
  5. Appendix: scope, limitations, methodology, legal/consent reference.
- **Branding:** wordmark, footer with report ID + generation timestamp + page numbers.
- **Accessibility:** selectable text, proper heading hierarchy, alt text for any chart; tagged PDF
  output from WeasyPrint must be validated before beta (see §14).
- **Renderer:** **WeasyPrint** (Python-native; lower RAM than Chromium/Playwright inside the worker).

---

## 7. Component library

> Implementation uses Tailwind CSS + shadcn/ui + Radix primitives. Components below are product
> components composed from those primitives.

### 7.1 Layout

| Component | Behavior | States |
|---|---|---|
| `AppShell` | Sidebar + content; skip link; landmarks | desktop, drawer |
| `Sidebar` | Wordmark, domain selector, nav, quota, user menu | expanded, collapsed/drawer |
| `DomainSelector` | Workspace domain context; "All domains" where allowed | loading, empty, selected |
| `PageHeader` | Title, subtitle, actions; optional back link | default, sticky on mobile |
| `MobileDrawer` | Focus-trapped drawer; Esc closes | open/closed |

### 7.2 Data display

| Component | Behavior | Accessibility |
|---|---|---|
| `KpiCard` | Label, value, delta, context, click target | `aria-label` includes full context |
| `ScoreGauge` | 0–100 or "Unscored"; coverage context always adjacent | Text equivalent; no color-only |
| `PostureTrendChart` | Score over scans; coverage annotations; tooltip | Data table fallback; keyboard tooltips |
| `SeverityBadge` | Color + icon + text | Never color-only |
| `StatusPill` | Scan/issue/PR status | Text label always present |
| `EnvironmentBadge` | Staging/Production | Icon + text |
| `CoverageReceipt` | Endpoints, classes attempted, blind spots | Semantic list/table |
| `PhaseTimeline` | 5 phases with states | `aria-live="polite"` summary, not every line |
| `LiveCounters` | Endpoints/tests/findings/requests/tokens | Throttled announcements |
| `RawLogViewer` | Virtualized monospace logs; pause auto-scroll | Keyboard scroll; copy |
| `EvidenceTabs` | PoC / HTTP / Patch | Proper tab semantics |
| `DiffViewer` | Syntax-highlighted diff; stacked on mobile | Line numbers, no color-only add/remove |
| `IssueStepper` | Detected → PR → Merged → Verified | `aria-current="step"` |
| `DataTable` | Sortable, filterable; responsive cards | Column headers, caption |
| `QuotaMeter` | Used/limit; warning at 80% | Text + progress semantics |

### 7.3 Feedback

| Component | Behavior |
|---|---|
| `Banner` | Inline, dismissible only if non-critical; variants info/warning/critical |
| `Toast` | Transient confirmations; not for critical errors |
| `EmptyState` | Icon + headline + explanation + one primary CTA |
| `ErrorState` | What happened, why (if known), what to do, request ID, retry |
| `Skeleton` | Layout-preserving placeholders |
| `ProgressCounter` | Live numeric progress with label |
| `ConfirmByTyping` | Requires exact domain name or `DELETE`; explains consequences |

### 7.4 Forms and overlays

| Component | Notes |
|---|---|
| `OAuthButton` | GitHub mark + label; loading state |
| `CopyField` | Copy button + "Copied" announcement |
| `MaskedSecretInput` | Show/hide, never logs value |
| `EnvironmentRadio` | Staging recommended; Production requires consent |
| `ConsentCheckbox` | Required; links to Rules of Engagement version |
| `Modal` / `Drawer` | Focus trap, Esc, restore focus |
| `Tooltip` | Supplementary only; never the sole source of meaning |

---

## 8. Design tokens

### 8.1 CSS variables (dark theme)

```css
:root {
  /* Approved palette */
  --color-bg: #0F1523;
  --color-secondary: #4A289A;
  --color-accent: #44ECF1;
  --color-text: #E8E8FA;

  /* Derived surfaces */
  --color-surface-1: color-mix(in srgb, var(--color-text) 4%, var(--color-bg));
  --color-surface-2: color-mix(in srgb, var(--color-text) 7%, var(--color-bg));
  --color-border: color-mix(in srgb, var(--color-text) 14%, transparent);
  --color-border-strong: color-mix(in srgb, var(--color-text) 24%, transparent);
  --color-text-muted: color-mix(in srgb, var(--color-text) 64%, var(--color-bg));
  --color-text-faint: color-mix(in srgb, var(--color-text) 42%, var(--color-bg));

  /* Semantic — PROPOSED, TBD sign-off */
  --color-critical: #FF6B81;
  --color-high: #FF9F43;
  --color-medium: #FFD166;
  --color-low: #7BD88F;
  --color-success: #3DDC97;
  --color-warning: #FFB020;
  --color-info: #8FB8FF;

  /* Typography */
  --font-display: "Syne", system-ui, sans-serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  /* Spacing (4px base) */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px; --space-10: 40px;
  --space-12: 48px; --space-16: 64px;

  /* Radius */
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 14px; --radius-full: 9999px;

  /* Focus */
  --focus-ring: 0 0 0 2px var(--color-bg), 0 0 0 4px var(--color-accent);

  /* Motion */
  --motion-fast: 120ms; --motion-base: 180ms; --motion-slow: 280ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
}
```

### 8.2 Tailwind mapping

- Colors map to `bg`, `surface`, `border`, `text`, `accent`, `secondary`, and semantic tokens.
- Use semantic class names (`text-critical`, `bg-surface-1`) — never raw hex in components.
- shadcn/ui CSS variables map to the same tokens; do not maintain a parallel palette.
- Dark mode is the default and only v1 theme; the PDF uses a separate print stylesheet.

### 8.3 Spacing, radius, elevation

- Spacing follows the 4px scale above; page gutters 24/32px; card padding 16/24px.
- Radius: inputs/buttons 10px; cards 14px; badges full.
- Elevation on dark: borders + subtle inner highlight, not heavy shadows. A cyan glow is reserved
  for focus/active, never for decoration.

### 8.4 Breakpoints

| Name | Min width | Layout |
|---|---|---|
| `sm` | 640px | 2-column KPI grid |
| `md` | 768px | 2-column content, tables scroll |
| `lg` | 1024px | Fixed sidebar, 4-column KPI grid |
| `xl` | 1280px | Full tables, side-by-side evidence |
| `2xl` | 1536px | Max content width 1440px |

---

## 9. Responsive behavior

### 9.1 Web

- **Desktop-first** (developers work on laptops). The primary design target is 1280–1440px.
- **< 1024px:** sidebar becomes a drawer; page header gains a menu button and compact domain selector.
- **375px:** all reading pages must work: Dashboard (KPI cards stack), Issues (cards instead of
  tables), Scan detail (timeline vertical, counters wrap), Issue detail (tabs scroll horizontally,
  diffs stacked). Code blocks may scroll horizontally but never the whole page.
- **Touch targets:** minimum 44×44px.
- **Sticky actions:** primary action (Run scan / Re-verify) remains reachable on mobile via a sticky
  bottom bar on detail pages.
- **Charts:** full-width, responsive, with a data-table fallback.
- **No horizontal page scroll** at any breakpoint; only code/log regions scroll horizontally.

### 9.2 Mobile app

- Android phone portrait first; tablets supported by responsive Flutter layouts.
- Bottom navigation with 3 tabs (Home, Issues, Activity); Login is outside the shell.
- Read-only surfaces; destructive/administrative actions deep-link to the web app.
- Pull-to-refresh; offline state shows last cached data with a "last updated" timestamp.
- Push notification tap deep-links to the relevant screen; if unauthenticated, login first, then
  deep-link.

---

## 10. Accessibility

**Target:** WCAG 2.1 Level AA.

- **Contrast:** ≥ 4.5:1 for body text; ≥ 3:1 for large text and UI boundaries. Deep Purple is never
  text on Dark Navy. Neon Cyan is not used for body copy.
- **Color independence:** every status uses color + icon + text. Severity and verification states
  must remain understandable in grayscale.
- **Keyboard:** all interactive elements reachable; visible focus ring (`--focus-ring`); logical tab
  order; Esc closes overlays; focus returns to the trigger.
- **Screen readers:** landmarks (`nav`, `main`), skip link, labelled forms, table captions,
  `aria-current` for nav/stepper. Live scan updates use a throttled `aria-live="polite"` summary
  (e.g., "Phase 3 of 5: confirming exploits; 12 findings so far"), not every log line.
- **Forms:** labels always visible; errors linked with `aria-describedby`; required fields marked;
  no placeholder-only labels.
- **Motion:** respect `prefers-reduced-motion`; no flashing; auto-scroll in logs pauses on hover/focus.
- **Zoom:** usable at 200% zoom; no loss of content.
- **PDF:** selectable text, heading hierarchy, alt text for charts; tagged PDF output from WeasyPrint
  must be validated before beta.
- **Testing:** automated axe checks in Playwright for core pages + manual keyboard/screen-reader
  passes before beta.

---

## 11. Content and microcopy

### 11.1 Terminology (UI ↔ data)

| UI term | Data entity | Notes |
|---|---|---|
| Issue | `findings` row | User-facing label is "Issue" |
| Scan / Episode | `scans` row | "Episode" only in technical/report contexts |
| Patch / PR | `patches` row | UI shows "PR" with a link to GitHub |
| Verified Fixed | `findings.status = verified_fixed` | Only after successful re-attack |
| Coverage Receipt | `scans.coverage` | Always available for completed/partial scans |
| Safe Mode | Production scan policy | Non-mutating checks, strict rate limit |
| Deep Mode | Staging scan policy | Active non-destructive checks |
| Unscored | Score state | Incomplete/blocked coverage |

### 11.2 Voice rules

- Specific over dramatic: "Missing `Content-Security-Policy` header on `/checkout`" not "Your site is
  vulnerable to attack!"
- Never say "100% secure", "hacker-proof", or "guaranteed".
- Zero findings headline: **"No vulnerabilities detected within tested scope."**
- Errors follow: **what happened → why (if known) → what to do → request ID**.
- No blame. No jargon without a tooltip or inline explanation.
- Numbers: use tabular numerals; show severity counts explicitly (e.g., "2 Critical, 3 High").

### 11.3 Status labels

| State | Label |
|---|---|
| Scan queued | Queued |
| Scan running | Running |
| Completed | Completed |
| Partial | Partial coverage |
| Blocked | Blocked by WAF |
| Unreachable | Target unreachable |
| Failed | Failed |
| Finding open | Open |
| PR ready | PR ready for review |
| Waiting deploy | Merged — waiting for deploy |
| Verifying | Re-verifying |
| Verified | Verified fixed |
| Still vulnerable | Still vulnerable |
| Suspected | Informational (not scored) |

---

## 12. State matrix

| Surface | Empty | Loading | Error | Success | Special |
|---|---|---|---|---|---|
| Dashboard | No domains → onboarding | KPI skeletons | Retry panel + request ID | Score + trend + issues | Unscored, live banner, WAF banner |
| Domains | Add first domain | Skeleton rows | Retry | Verified + repo connected | Unverified, disconnected, quota |
| Scan detail | No scan selected | Phase timeline + counters | Failed/blocked/unreachable | Completed + report | Partial, cancelled, queued |
| Issues | No issues → Coverage Receipt | Skeleton list | Retry | Confirmed list | Suspected section, filtered-empty |
| Issue detail | — | Skeleton | Retry | Stepper + evidence | False positive, won't fix, regression |
| PR Reviews | No PRs | Skeleton | Retry | PR status mirror | CI failed, needs rebase, closed |
| Settings | — | Skeleton | Inline errors | Saved toast | Disconnected GitHub, quota warning |
| Mobile | No domains | Pull-to-refresh spinner | Retry | Cards + score | Offline cached data |

---

## 13. UI/UX acceptance criteria

### 13.1 Global

- [ ] All 6 web pages + auth + onboarding render at 375px, 768px, 1024px, 1440px with no page-level
      horizontal scroll.
- [ ] Every status is conveyed by color + icon + text; grayscale screenshots remain understandable.
- [ ] All interactive elements are keyboard reachable with visible focus; overlays trap and restore
      focus.
- [ ] axe-core reports zero serious/critical violations on Dashboard, Issues, Issue detail, Scan
      detail, Settings.
- [ ] Every page has a loading skeleton, empty state, and error state with a retry action.
- [ ] No screen claims "100% secure"; zero-finding scans show the Coverage Receipt.
- [ ] The primary action per page is visually dominant and consistent in position.
- [ ] All timestamps are localized; technical logs show UTC.
- [ ] No secret, token, cookie, or PII appears in the UI, logs, URLs, or PDF.
- [ ] The PDF is 4–8 pages, light theme, no cyan text on white, and includes the Coverage Receipt.

### 13.2 Journey acceptance (Playwright-mappable)

- [ ] **Onboarding:** sign-in → add domain → verify (mocked DNS/file) → consent → first scan starts
      within one session; reload mid-flow resumes at the correct step.
- [ ] **Verification failure:** wrong TXT/file shows a specific reason; Retry and Alternative Method
      work.
- [ ] **Scan-only:** no repo → issues + Coverage Receipt + PDF download; CTA to connect GitHub is
      visible on each issue.
- [ ] **Grey-box:** repo linked → scan → PR appears in PR Reviews; issue stepper shows PR Opened.
- [ ] **Merge → re-attack:** merge webhook → "Merged — Waiting for Deploy" → Re-verify Now →
      "Verified Fixed" and score increases only after verification.
- [ ] **Close PR:** issue remains Open; False Positive/Won't Fix actions work; no automatic reopen.
- [ ] **CI failure:** PR shows CI Failed; Regenerate Fix accepts a note.
- [ ] **WAF block:** banner appears; scan is Blocked/Partial; Coverage Receipt lists affected paths.
- [ ] **Zero findings:** headline is the approved wording; Coverage Receipt is present; no green
      "100% secure" state.
- [ ] **Quota:** at 5/5 scans, manual scan is disabled with reset date; dashboard remains readable.
- [ ] **Deletion:** typed confirmation required; running scan stops; domain data disappears; audit
      notice shown.
- [ ] **Mobile deep link:** push notification opens the correct screen; unauthenticated users are
      routed through login and then to the target.

### 13.3 Performance budgets (proposed, TBD sign-off)

- LCP < 2.5s on a mid-range laptop over broadband for Dashboard/Issues.
- INP < 200ms; CLS < 0.1.
- Live logs remain responsive with 5,000+ events (virtualized).
- PDF generation completes within 60s for a standard report.

### 13.4 Test selectors

- Stable `data-testid` attributes on: `run-scan`, `add-domain`, `verify-domain`, `consent-checkbox`,
  `scan-status`, `phase-timeline`, `coverage-receipt`, `issue-row`, `issue-stepper`,
  `pr-status`, `regenerate-fix`, `reverify-now`, `quota-meter`, `confirm-typing`, `report-download`.
- Selectors must not depend on visual classes or copy that is likely to change.

---

## 14. Open design items (TBD)

| Item | Status | Decision / next step |
|---|---|---|
| Logo symbol | TBD | Wordmark-only until a designer delivers |
| Body font | **Decided** | Inter (with Syne for headings, JetBrains Mono for code/logs) |
| Semantic status palette | Proposed | Sign off after contrast/color-blind validation |
| PDF renderer | **Decided** | WeasyPrint (see `plan.md` §7) |
| Chart library | **Decided** | Recharts via shadcn charts |
| Empty-state illustrations | Not planned | Icon + copy only in v1 |
| Tagged/accessible PDF | TBD | Validate WeasyPrint tagged output before beta |
| Arabic/RTL | v2 | Do not hard-code direction-sensitive layouts |
| Marketing site | Out of v1 | Not part of the product app |
