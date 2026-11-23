# Mirsad (مرصاد)

Continuous, evidence-based application security for mid-size teams:
**Red finds and proves → Blue patches via GitHub PR → human merges → Red re-attacks and verifies.**
No auto-merge. No destructive tests. Honest coverage reporting.

> Status: **v1 Beta — Phase 0 (Foundation) in progress.** See `plan.md` §3.2 for the phase map.
> This repository is governed by `AGENTS.md` (non-negotiable agent/contributor rules).

## Source of truth

| Document | Role |
|---|---|
| `plan.md` | Technical architecture, data model, deployment, release gates |
| `design.md` | UX/UI behavior and visual rules |
| `AGENTS.md` | Repository rules for coding agents and contributors |

## Repository layout (plan.md §6)

```
apps/web          Next.js web app (App Router, TypeScript strict, Tailwind)
apps/mobile       Flutter Android owner companion (later phase)
services/api      FastAPI API (Python 3.12, Pydantic v2)
services/worker   Python worker + LangGraph agents (Phase 1+)
packages/shared   Shared schemas/types (OpenAPI-generated TS client)
supabase          Migrations, RLS policies, RLS tests
tests/e2e         Playwright
infra             Dockerfiles, platform configs, scripts
```

## Local development (dev environment)

Prerequisites: Node ≥ 20.9, Docker, [uv](https://docs.astral.sh/uv/), Supabase CLI.

```bash
# 1. Local Supabase (Auth/Postgres/Storage/Realtime)
supabase start
supabase db reset          # applies supabase/migrations

# 2. Web
npm ci
cp apps/web/.env.example apps/web/.env.local   # fill from `supabase status`
npm run dev --workspace apps/web

# 3. API
cd services/api
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 4. Tests
cd services/api && uv run pytest          # unit; add -m integration with local DB
cd supabase && uv run pytest              # RLS isolation, audit immutability, bootstrap
npm run lint && npm run typecheck && npm run test --workspace apps/web
npm run test:e2e             # Playwright (requires local Supabase + web)
```

Environment variables: see `.env.example` (placeholder names only; real values live in
platform secret stores or git-ignored local files — never in git).

## Conventions

- Conventional Commits; small reversible changes; PR review required (`AGENTS.md` §11).
- TypeScript strict; Python 3.12 with type hints; SQL migrations append-only.
- Design tokens from `design.md` §8 — no raw hex values in components.
- Security suite must stay 100% green; never skip or weaken security tests.
