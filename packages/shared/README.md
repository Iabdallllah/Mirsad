# @mirsad/shared

Shared API types for web/mobile, **generated from the FastAPI OpenAPI
document** — never hand-written twice (plan.md §6 convention).

## Regenerate

```bash
# 1. Export the OpenAPI document from the API (local dev server running):
curl -s http://localhost:8000/openapi.json > ../../services/api/openapi.json

# 2. Generate TypeScript types:
npm run generate --workspace packages/shared
```

`src/generated/api.ts` is committed so consumers can typecheck without a
running API. Regenerate whenever `services/api` schemas change, in the same
PR (contract tests, plan.md §13.1).
