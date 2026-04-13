# CartWise — Implementation Phases

## How this file works

1. Requirements are expressed in `REQUIREMENTS.md`
2. Requirements are broken down into phases here
3. As each phase completes, both `REQUIREMENTS.md` and this file are updated
4. Each phase ends with passing tests and a commit

---

## Phase 1: MenuItem Model Overhaul

**Status:** Complete (PR #36)

Merge `recipe` + `ingredients` into single `body` field. Remove fork endpoint. Add unarchive. Update correlation pipeline.

---

## Phase 2: Meal Plan Ordering

**Status:** Complete (PR #37)

Add `rank` column to `meal_plan_items`. Enriched response nests full `MenuItemResponse`. Rename `/me` routes to `/{user_id}`.

---

## Phase 3: User Model + Onboarding

**Status:** Complete (PR #39)

Add `splitwise_user_id` to users. New `POST /auth/onboard` endpoint. Remove auto-create from `GET /auth/me`. Hardcode INR.

---

## Phase 4: Order Lifecycle + Splits Table

**Status:** Complete (PR #40)

New `splits` table. Order status: draft → completed | cancelled. Cancel, edit-splits, approve endpoints. Open order visibility.

---

## Phase 5a: Frontend API Client Layer

**Status:** Complete (PR #41)

`openapi-typescript` + `openapi-fetch` + `openapi-react-query` + `@tanstack/react-query`. Generated types from backend OpenAPI spec. Typed fetch client with auth middleware. QueryClientProvider in root layout.

---

## Phase 5b: Auth + Onboarding Flow

**Status:** Not started

**Screens:** Sign In (`/login`), Onboarding (`/onboarding`)

This is the gateway — nothing works without it. Must be built first.

| Task | Detail |
|---|---|
| Supabase client setup | `lib/supabase.ts` — browser client with `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Auth guard middleware | Next.js middleware or layout-level check: no Supabase session → `/login`, session but no DB user (GET /auth/me → 404) → `/onboarding`, otherwise → allow |
| Sign In page (`/login`) | Supabase Auth UI with Google provider. Single button: "Sign in with Google". Redirects to onboarding or home based on `GET /auth/me` response. |
| Onboarding page (`/onboarding`) | Form: name (pre-filled from Google), phone (10 digits), Splitwise User ID (integer). Calls `POST /auth/onboard`. On success → redirect to `/`. |
| Wire auth middleware to API client | Replace localStorage token with Supabase session token in `lib/api/client.ts` auth middleware |
| Top bar component | Global header: CartWise logo (centre), user avatar (right → `/profile/[id]`), back arrow on sub-pages. Used by all subsequent screens. |

**Depends on:** Phase 5a

**Verify:** Sign in with Google → onboarding form → complete → land on home. Refresh → stays signed in. Sign out → back to login.

---

## Phase 5c: Home + Meal Plan Flow

**Status:** Not started

**Screens:** Home (`/`), Meal Plan Edit (`/meal-plan/edit`), Meal Plan Reorder (`/meal-plan/reorder`)

The main screen users see after sign-in. Core meal plan management loop.

| Task | Detail |
|---|---|
| Home page (`/`) | Fetch `GET /meal-plans/{user_id}`. Show ordered list of MenuItem names. [Edit] button → Meal Plan Edit. Empty state: plus icon + "No items in your meal plan." CTA "New Split" button (hidden if empty). |
| Meal Plan Edit (`/meal-plan/edit`) | Fetch `GET /menu-items/?created_by={user_id}` (own items, active only). Checkbox list with two tap zones (checkbox toggles, name navigates to detail). Search bar (heading + body). Sort: relevance (checked first) / alphabetical / recently updated / least recently updated. [+ Create New] → MenuItem Editor (Phase 5d). [OK] → Reorder. [Cancel] → Home. |
| Meal Plan Reorder (`/meal-plan/reorder`) | Show checked items only. Drag-and-drop or up/down arrows to set order. [Done] → `PUT /meal-plans/{user_id}` with ordered list → Home. [Cancel] → Home (discard). |
| State management | Meal Plan Edit and Reorder share local state (checked items + order). Single `PUT` call on Done. |

**Depends on:** Phase 5b (auth guard, top bar)

**Verify:** Home shows meal plan. Edit → check/uncheck items → OK → reorder → Done → Home shows updated plan. Empty state works. Search and sort work.

---

## Phase 5d: Menu Items Flow

**Status:** Not started

**Screens:** MenuItem Detail (`/menu-items/[id]`), MenuItem Editor (`/menu-items/[id]/edit` or `/menu-items/new`)

CRUD for MenuItems. Created from Meal Plan Edit's [+ Create New] button.

| Task | Detail |
|---|---|
| MenuItem Detail (`/menu-items/[id]`) | Fetch `GET /menu-items/{id}`. Full-page markdown viewer: headline (name) + rendered body. Actions: [Edit] → Editor, [Add to Plan] / [Remove from Plan] (switches based on plan status, calls `POST` or `DELETE` on meal plan items), [Archive] / [Unarchive] (calls `PATCH /menu-items/{id}/archive` or `/unarchive`). |
| MenuItem Editor (`/menu-items/[id]/edit`, `/menu-items/new`) | Form: name (text field) + body (textarea, markdown). [Save] → `POST /menu-items/` (new) or `PATCH /menu-items/{id}` (edit) → back to Detail or Meal Plan Edit. [Cancel] → back. |
| Markdown rendering | Use a markdown renderer (e.g. `react-markdown`) for the body field in Detail view. |
| Add/Remove from plan | Detail page checks if item is in current plan (from meal plan data). Button switches label accordingly. Add → goes to Reorder → back to Detail. Remove → confirmation → stays on Detail. |

**Depends on:** Phase 5c (Meal Plan Edit has [+ Create New] that opens Editor; Detail has Add/Remove from Plan)

**Verify:** Create new item from Meal Plan Edit → save → back to edit (auto-checked). Open item detail → edit → save. Archive → auto-removes from plan. Unarchive. Add to plan / remove from plan.

---

## Phase 5e: Invoice Wizard Flow

**Status:** Not started

**Screens:** Invoice Setup (`/invoice`), Split Analysis (`/invoice/review`), Split Result (`/invoice/result`)

The core product flow. 3-step wizard with stepper dots.

| Task | Detail |
|---|---|
| Wizard shell | Stepper dots (3 steps, no labels). Discard confirmation on navigate away. Rehydrate from existing draft on mount (`GET /orders/?status=draft`). |
| Step 1: Invoice Setup (`/invoice`) | PDF upload area (file picker + share target on Android). Participant selector: user search → filtered dropdown (name + avatar) → chip added. Payer chip distinct style, non-removable. Participants cached in localStorage. [Analyse] → `POST /orders/` (multipart: file + participant_ids) → Step 2. Disabled until file + at least 1 other participant. |
| Step 2: Split Analysis (`/invoice/review`) | Two modes via toggle: **View Mode** (default) — participant avatars with grocery item names grouped under each. **Edit Mode** — grocery items as rows with participant chips, tap to add/remove. Unaccounted section at bottom. [Save edits] → `PUT /orders/{id}/splits` (sends assignments, backend recomputes). [Approve] → `POST /orders/{id}/approve` → Step 3. [Back] → discard confirmation → `PATCH /orders/{id}/cancel` → Home. |
| Step 3: Split Result (`/invoice/result`) | Per-split success/failure icons. Splitwise response data. [Done] → Home. |
| Share target integration | Wire existing `/share` page into wizard Step 1 (file comes from service worker Cache API). |

**Depends on:** Phase 5c (Home has "New Split" CTA), Phase 5b (auth, user data for participant search)

**Verify:** Upload PDF → analyse → review splits → edit assignments → approve → see results. Cancel flow. Share from another app (Android). Refresh on Step 2 → rehydrates from draft.

---

## Phase 5f: Profile + Invoice History

**Status:** Not started

**Screens:** Profile (`/profile/[id]`), Split Detail (`/invoices/[id]`)

Read-only views. Last to build because they display data from all other flows.

| Task | Detail |
|---|---|
| Profile page (`/profile/[id]`) | Top section: avatar, name, email, phone, Splitwise ID (all read-only). [Sign out] (self only). Tabs differ by viewer: **Self** (3 tabs): Meal Plan, Menu Items (includes archived with badge), Invoices. **Others** (2 tabs): Meal Plan, Invoices. Meal Plan tab: ordered list, names only, read-only. Menu Items tab (self): all items including archived, tappable → Detail. Invoices tab: `GET /orders/?user_id={id}` filtered to completed. |
| `/profile/me` redirect | Client-side: read user ID from auth state, navigate to `/profile/{id}`. |
| Split Detail (`/invoices/[id]`) | Fetch `GET /orders/{id}`. Show: date, filename, status, total. Extracted items section. Split groups section (amount → members). Splitwise audit log section (per-expense success/failure). |
| Invoices list | Each entry: date, filename, status, total. Tap → Split Detail. |

**Depends on:** Phase 5e (invoices are created by the wizard), Phase 5d (Menu Items tab links to Detail)

**Verify:** View own profile (3 tabs). View other's profile (2 tabs, no Menu Items). Sign out. View invoice detail. `/profile/me` redirects.

---

## Dependency Graph

```
Phase 1 (MenuItem) ──► Phase 2 (Meal Plan) ──┐
                                              │
Phase 3 (Onboarding) ──► Phase 4 (Orders) ──►│
                                              │
                                    Phase 5a (API Client)
                                              │
                                    Phase 5b (Auth + Onboarding)
                                              │
                                    Phase 5c (Home + Meal Plan)
                                              │
                                    Phase 5d (Menu Items)
                                              │
                                    Phase 5e (Invoice Wizard)
                                              │
                                    Phase 5f (Profile + History)
```

Phases 5b–5f are strictly sequential — each screen flow builds on the previous.
