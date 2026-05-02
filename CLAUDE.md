# cartwise

Grocery cost splitting with meal planning — monorepo.

## Structure

```
backend/   — FastAPI API server (Python)
ui/        — Frontend (Next.js + React + Tailwind)
```

## Orientation

- @backend/CLAUDE.md — backend-specific orientation, key files, commands
- @backend/docs/architecture.md — data flow, DB schema, auth, AI layer
- @CONTRIBUTING.md — prerequisites, quick start, workflow

## Important Principles

- **Never justify cutting corners (security, architecture, best practices) by citing project size, user count, or cost or any excuse. Do things the right way. Never ever justify this with small app, poc, locally usable etc.
- **Secrets are secrets.** Store them in proper secret management (Secret Manager, or some XYZ vault), not plaintext env vars. This applies regardless of who has access today.
- **Each system owns only its secrets.** GitHub Secrets hold only what CI needs. Cloud Run / Secret Manager hold only what runtime needs. No duplication.
- **Never run migrations manually against production.** Migrations run via GitHub Actions on deploy. Only run locally against dev/test databases.
- **Never run database mutating queries manually against production.** Only run locally against dev/test databases. Or unless user approves it and knows about it.
- **Non-secret config belongs in code.** If a value isn't secret, it goes in `settings.toml` (version-controlled, reviewable). Env vars are only for secrets and deploy-specific overrides (like CORS origins that depend on the Vercel URL).

## Deployment

| Component | Platform | Deploy trigger |
|-----------|----------|----------------|
| Backend | Google Cloud Run | Push to `main` (GitHub Actions) |
| Frontend | Vercel | Push to `main` (auto) |
| Database + Auth + Storage | Supabase | Managed |

- Backend URL: `https://cartwise-backend-477485410657.asia-south1.run.app`
- Frontend URL: `https://cartwise-amber.vercel.app`
- Supabase project: `zwtqhrwsbmbuhwqcvrmj`
