# Architecture

## Overview

CartWise is a grocery cost splitting backend. Users create menu items (recipes),
build meal plans, and when someone buys groceries, the system automatically
determines which grocery items each person uses and splits the cost accordingly.

The key insight: cost splitting is modeled as a **bipartite graph** between
grocery items and members. Items with identical member neighbor sets collapse
into a single split group — producing the minimum number of transactions.

## Data flow

```
Client (future: Next.js frontend)
  │
  │  Bearer JWT (issued by Supabase Auth)
  ▼
FastAPI (/api/v1/...)
  │
  ├─ Middleware: RequestLogging (request ID + latency)
  ├─ Middleware: CORS
  ├─ Error handlers (consistent JSON responses)
  │
  ├─ /auth/me          → validate JWT, find/create user
  ├─ /users            → CRUD
  ├─ /menu-items       → CRUD + fork + archive
  ├─ /meal-plans       → get/set/add/remove per user
  └─ /orders           → upload PDF → pipeline → splits
       │
       ▼
  Order pipeline (synchronous, ~15s):
       │
       ├─ 1. save_upload()          → Supabase Storage (or local disk)
       │
       ├─ 2. _snapshot_meal_plans() → freeze participants' plans at this moment
       │     builds: members = {user_id: [menu_item_ids]}
       │             menu_items = [{id, name, ingredients}]
       │
       ├─ 3. extract(pdf_path)      → pdfplumber (sync, via asyncio.to_thread)
       │     parses invoice tables, extracts line items
       │     returns: {invoices: [{page, items: [{upc, description, hsn, mrp, qty, total}]}]}
       │
       ├─ 4. classify(extracted)    → LiteLLM → LLM
       │     for each row: "item" (product) or "fee" (delivery/handling)
       │     returns: {summary: {item_total, fee_total, grand_total}, items: [...]}
       │
       ├─ 5. correlate(menu_items, grocery_items) → LiteLLM → LLM
       │     for each MenuItem: send name+ingredients + all GroceryItems
       │     LLM returns matched UPCs
       │     returns: {menu_item_id: [upc, ...]}
       │
       ├─ 6. compute_splits()       → pure computation, no I/O
       │     builds bipartite graph: GroceryItem ↔ Member
       │     groups by identical member neighbor sets (frozenset key)
       │     returns: {paidBy, splits: [{amount, groceryItems, splitEquallyAmong}]}
       │
       └─ 7. Store → Order.snapshot (JSONB) + Order.result (JSONB)
```

## Bipartite graph model

The cost splitting algorithm works by building a bipartite graph between grocery
items and members, then grouping items by their member neighbor set.

```
Members              GroceryItems
  │                      │
  Alice ─── Chicken Curry uses ──── Chicken Breast (₹289)
  │    └─── Green Salad uses ──┬── Cucumber (₹26)
  │                            ├── Cherry Tomato (₹32)
  Bob ──── Green Salad uses ───┘── Lemon (₹38)
  │
  Carol ─── Milk Tea uses ──────── Amul Milk (₹83)
```

**Neighbor sets:**
- Chicken Breast → {Alice} (only Alice's curry uses it)
- Cucumber, Cherry Tomato → {Alice, Bob} (both have salad)
- Lemon → {Alice, Bob} (salad uses it)
- Amul Milk → {Carol}
- Fees → {Alice, Bob, Carol} (everyone)

**Grouped by identical neighbor sets:**
```
{Alice}            → ₹289 (chicken)
{Alice, Bob}       → ₹96  (salad items + lemon)
{Carol}            → ₹83  (milk)
{Alice, Bob, Carol} → ₹11  (fees)
```

Each group = one split transaction. This is the minimum number of transactions.

## Database schema

```
┌──────────────┐     ┌──────────────────┐
│    users     │     │   menu_items     │
├──────────────┤     ├──────────────────┤
│ id (UUID PK) │◄────│ created_by (FK)  │
│ email        │◄────│ updated_by (FK)  │
│ name         │     │ id (UUID PK)     │
│ phone        │     │ name             │
│ avatar_url   │     │ recipe (text/md) │
│ oauth_provider│    │ ingredients (text)│
│ oauth_id     │     │ status           │
│ is_active    │     │ created_at       │
│ created_at   │     │ updated_at       │
│ updated_at   │     └──────────────────┘
└──────────────┘              │
       │                      │
       │ 1:1                  │ M:N
       ▼                      ▼
┌──────────────┐     ┌──────────────────┐
│  meal_plans  │     │ meal_plan_items  │
├──────────────┤     ├──────────────────┤
│ id (UUID PK) │◄────│ meal_plan_id(FK) │
│ user_id (FK) │     │ menu_item_id(FK) │
│ updated_at   │     └──────────────────┘
└──────────────┘

┌──────────────┐     ┌────────────────────┐
│    orders    │     │ order_participants │
├──────────────┤     ├────────────────────┤
│ id (UUID PK) │◄────│ order_id (FK)      │
│ paid_by (FK) │     │ user_id (FK)       │
│ invoice_file │     └────────────────────┘
│ status       │
│ snapshot (J) │  ← frozen meal plans at order time
│ result (J)   │  ← split output
│ created_at   │
└──────────────┘
```

All tables use UUID primary keys with server-side `gen_random_uuid()` defaults.
Timestamps use `TIMESTAMPTZ` with `now()` server defaults.

## Auth flow

```
Frontend                    Supabase Auth                Our Backend
   │                              │                          │
   │ signInWithOAuth("google")    │                          │
   │─────────────────────────────>│                          │
   │                              │ OAuth flow with Google   │
   │ JWT (access_token)           │                          │
   │<─────────────────────────────│                          │
   │                                                         │
   │ GET /api/v1/auth/me                                     │
   │ Authorization: Bearer <jwt>                             │
   │────────────────────────────────────────────────────────>│
   │                                                         │ validate JWT
   │                                                         │ (SUPABASE_JWT_SECRET)
   │                                                         │ find user by oauth_id
   │                                                         │ or auto-create
   │ {id, email, name, ...}                                  │
   │<────────────────────────────────────────────────────────│
```

- We do NOT handle OAuth flows — Supabase does everything
- Backend validates Supabase-issued JWTs using the project's JWT secret
- First login auto-creates the user from JWT claims (`sub`, `email`, `user_metadata`)
- Dev-only: `POST /auth/dev-login` creates users + returns JWT (when `DEBUG=true`)

## AI layer

```
app/services/classify.py ──┐
                           ├──> app/ai/client.py ──> litellm.acompletion()
app/services/correlate.py ─┘         │
                                     │
                          ┌──────────┴──────────┐
                          │   AI_PROVIDER config │
                          ├──────────────────────┤
                          │ ollama/qwen2.5:3b    │  ← local (default)
                          │ anthropic/claude-3.. │  ← cloud
                          │ gpt-4o-mini          │  ← cloud
                          └──────────────────────┘
```

**`app/ai/client.py`** is a thin wrapper around `litellm.acompletion()`. It:
- Reads `AI_PROVIDER`, `AI_MODEL`, `AI_BASE_URL`, `AI_API_KEY` from Dynaconf
- Builds the LiteLLM model string (`provider/model`)
- Sends system prompt + user prompt + JSON schema
- Returns parsed dict

Swap models by changing config — no code changes needed.

**Structured output** is enforced via `response_format.json_schema`. The LLM
must return JSON matching the provided schema. Classify uses
`{category: "item"|"fee"}`, correlate uses `{matched_upcs: [string]}`.

## Config system

```
settings.toml          committed — structure, defaults, non-secret values
     +
.secrets.toml          gitignored — credentials per environment
     +
CARTWISE_* env vars   highest priority — CI and production overrides
     =
Dynaconf settings     app/config.py → settings.DATABASE_URL, settings.AI_MODEL, etc.
```

**Profiles** are switched via `CARTWISE_ENV`:
- `development` — local Docker Postgres, debug mode, dev JWT secret
- `testing` — test Postgres on port 5433, test JWT secret, Ollama on localhost
- `production` — Supabase Postgres, real JWT secret, cloud LLM

## File storage

PDFs are stored in **Supabase Storage** (private `invoices` bucket) in production.
Path: `orders/{order_id}/invoice.pdf`.

Falls back to **local disk** (`STORAGE_DIR/orders/{order_id}/invoice.pdf`) when
`SUPABASE_URL` is not a real Supabase URL (testing/local dev).

`download_to_temp()` retrieves the PDF to a local temp file for pdfplumber,
which requires a filesystem path.

## Key files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app, middleware, routers |
| `app/config.py` | Dynaconf settings instance |
| `app/database.py` | Async SQLAlchemy engine + session dependency |
| `app/ai/client.py` | LiteLLM wrapper |
| `app/auth/jwt.py` | Supabase JWT validation |
| `app/auth/dependencies.py` | `CurrentUser` dependency |
| `app/models/*.py` | SQLAlchemy ORM models |
| `app/schemas/*.py` | Pydantic request/response schemas |
| `app/routes/*.py` | API endpoint handlers |
| `app/services/extract.py` | PDF → structured line items (pdfplumber) |
| `app/services/classify.py` | Line items → item/fee classification (LLM) |
| `app/services/correlate.py` | MenuItem ↔ GroceryItem matching (LLM) |
| `app/services/split.py` | Bipartite grouping → minimum split transactions |
| `app/services/storage.py` | PDF upload/download (Supabase Storage / local) |

## Dependency choices

**FastAPI** — async-first, Pydantic-native, auto OpenAPI docs. The standard for
modern Python APIs.

**SQLAlchemy 2.0 (async)** — mature ORM with typed `Mapped[]` columns and
`async_sessionmaker`. Paired with `asyncpg` for PostgreSQL.

**Alembic (async template)** — autogenerate migrations from model diffs. The
standard for SQLAlchemy schema management.

**LiteLLM** — unified interface to 100+ LLM providers. `acompletion()` with the
same API regardless of whether you're calling local Ollama or cloud Anthropic.
Model is just a config string.

**Dynaconf** — Spring Boot-style config with TOML files, environment sections,
secrets separation, and env var overrides. Closest Python equivalent to
`application.yml`.

**Supabase** — managed Postgres + Auth + Storage. Auth handles the full OAuth
flow; backend just validates JWTs. Storage handles PDF uploads without S3/GCS
setup.

**structlog** — structured logging with JSON output in production and
human-readable console in dev. Request IDs via contextvars for traceability.

**pdfplumber** — deterministic PDF table extraction. No ML, no heuristics — just
reads the table structure. Sync library, called via `asyncio.to_thread()`.
