# CartWise UI — Requirements

## Status: Draft (reviewed, addressing discrepancies)

---

## Core Principle

The app is useless without sign-in. Every flow starts with authentication.

---

## Authentication

- Google Sign-In (via Supabase Auth)
- If not signed in → redirect to sign-in page
- Session persists across app restarts (Supabase handles token refresh)

---

## Onboarding (part of sign-in)

- Supabase session exists post-OAuth, but the app treats the user as unauthenticated for all routes except `/auth/me` and `/auth/onboard` until the DB user record is created via onboarding.
- The backend creates the user record only when onboarding is submitted (`POST /auth/onboard`) — no user row exists before that.
- Frontend flow: after OAuth → call `GET /auth/me` → if 404 → show onboarding → if 200 → go to home.
- **All fields mandatory:**
  - Name (pre-filled from Google)
  - Phone (freeform text, 10 digits)
  - Splitwise User ID (integer — see Splitwise User Mapping section below)
- Once set, these fields become **read-only forever** (no editing after onboarding)
- If user closes app mid-onboarding and returns → Supabase session persists (no re-OAuth needed), but the onboarding form is shown again with empty fields since no partial user record exists in the DB.

---

## Top Bar (global, all pages)

- **Centre**: CartWise logo/icon (static — tapping does **nothing**)
- **Top-right**: user avatar (tapping → your profile at `/profile/[id]`)
- Sub-pages show a **back arrow** on the left (standard browser/OS back navigation)
- **No bottom tab bar** anywhere in the app

---

## Home Page (post sign-in + onboarding)

### 1. Current Meal Plan

- Shows the user's current meal plan as an ordered list of MenuItems
- Each MenuItem displays: name
- The meal plan is a **set** (no duplicates) but **ordered** (user can reorder)
  - Backend rejects duplicate `menu_item_ids` with 400 error (no silent deduplication)
- **Tap a MenuItem** → full page MenuItem Detail viewer
- **Tap Edit** → Meal Plan Edit screen (checkboxes for your own MenuItems)
- **Empty state**: plus icon + "No items in your meal plan. Tap to add some." (plus icon = same as Edit, goes to Meal Plan Edit)

### 2. Call-to-Action: New Split

- Prominent button to start the invoice/split flow
- **Only visible when meal plan has at least one item** (hidden when empty)
- Label: TBD

---

## MenuItems

- Users can only see and manage **their own** MenuItems
- **CRUD operations:**
  - **Create** new MenuItems (name + body as markdown)
  - **Edit** their own MenuItems
  - **Archive** MenuItems they no longer use — **archiving auto-removes the item from the user's meal plan**
  - **Unarchive** previously archived MenuItems
- Archived items are hidden from Meal Plan Edit — cannot be re-added while archived
- MenuItem has: name (headline) + body (single markdown field containing recipe, ingredients, everything)
- Creator info is implicit — users only see their own items, so no need to display who created it

---

## Meal Plan Edit

- Full screen showing **only your own MenuItems** as a checkbox list
- Each row has two interaction zones:
  - **Checkbox** (left): toggles the item in/out of the meal plan
  - **Name area** (right of checkbox): tappable → navigates to MenuItem Detail
- Currently selected items (in plan) appear **checked**
- **Search bar** at top: searches MenuItem **heading AND body**
- **Sort options**: relevance (selected items first, then alphabetical), alphabetical, recently updated (newest first), last updated (oldest first)
  - Default sort is "relevance" — selected/checked items appear higher, even with no search query
- Archived items are **not shown**
- **"Create new" button** — the **only way** to create a new MenuItem in the entire app
  - Tapping → MenuItem Editor (empty) → save → back to Meal Plan Edit with new item auto-checked
- **[OK]** → navigates to Meal Plan Reorder
- **[Cancel]** → back to Home

---

## Meal Plan Reorder

- Shows only the selected/checked MenuItems
- Drag-and-drop or up/down arrows to set order
- **Always shown** after Meal Plan Edit OK (even for single item)
- **[Done]** → saves order, back to Home
- **[Cancel]** → back to Home (discards changes)
- Backend change: `meal_plan_items.position` integer column (migration)

---

## MenuItem Detail (full page)

- **Full page markdown viewer** — only accessible for your own MenuItems
- Top: headline (MenuItem name)
- Body: single markdown field rendered (recipe + ingredients together)
- **Affordances:**
  - [Edit] → MenuItem Editor → save → back to viewer
  - [Add to Plan] / [Remove from Plan] → **button switches** depending on current plan status
    - Add → Meal Plan Reorder → save → back to viewer
    - Remove → confirms removal → stays on viewer
  - [Archive] / [Unarchive] → toggles status
- Back → previous screen

---

## MenuItem Editor (full page)

- **Headline**: editable text field (MenuItem name)
- **Body**: single editable text area (markdown) — contains recipe AND ingredients together
- No separate ingredients field — it's all one body
- **[Save]** → saves, back to MenuItem Detail (or back to Meal Plan Edit if creating new)
- **[Cancel]** → back to previous screen

---

## MenuItem Creation Flow

- **Only from Meal Plan Edit → "Create new" button**
- Opens MenuItem Editor (empty fields)
- Save → new MenuItem created globally (owned by current user)
- Returns to Meal Plan Edit with the new item auto-checked
- No other way to create MenuItems in the app

---

## Invoice / Split Wizard (3 steps)

**Stepper at top**: three dots indicating current step (no labels, just dots).
No bottom tabs during the wizard.
**Wizard state rehydrates from backend.** If the user refreshes the page on Step 2, the frontend checks for an existing draft order (`GET /orders/?status=draft`) and reloads the split data from it. If the user navigates away (taps avatar, browser back), a confirmation dialog asks "Discard current progress?" — if they confirm, the draft order is cancelled and they leave.

### Order Lifecycle

The wizard creates an order record at Step 1 (`[Analyse]`). The lifecycle:
- **`[Analyse]`** → creates order with status `"draft"` + split rows from computed result
- **Edit splits** (Step 2, optional) → user edits member assignments → `PUT /orders/{id}/splits` → backend recomputes amounts from original prices → updates split rows
- **`[Approve]`** (Step 2) → `POST /orders/{id}/approve` → pushes each split to Splitwise → transitions to `"completed"`
- **`[Discard]`** (Back from Step 2, or navigate away) → `PATCH /orders/{id}/cancel` → transitions to `"cancelled"`
- If the user closes the browser tab mid-wizard, the order remains `"draft"`. A background cleanup or next-login cleanup can handle these.
- Backend change: order status values become `"draft"` → `"completed"` | `"cancelled"`. Add cancel/delete endpoint.

### Step 1: Invoice Setup (`/invoice`)

- Upload a grocery invoice PDF (file picker + share target on Android)
- Select participants:
  - **Current user (payer) always included**, shown as a **visually distinct chip** (different color/border, non-removable)
  - User search: type name → filtered dropdown showing **name + avatar** → select → chip added
  - **Cached locally**: last participant selection pre-filled from localStorage
  - No saved groups — just cached last selection
- **[Analyse]** → sends to backend → navigates to Step 2

### Step 2: Split Analysis & Review (`/invoice/review`)

Two views of the split result:

#### View Mode (default): Participant → GroceryItems
- Each participant shown by **avatar only**
- Under each: list of grocery item **names only** (no prices)
- Clean, scannable — "who gets what"

#### Edit Mode (toggle): GroceryItem → Participants
- Each grocery item shown as a row
- Under each: participant chips showing **name + avatar**
- Tap to add/remove participants from a grocery item (including the payer — payer is non-removable from the invoice participant set, but can be added/removed from individual items)
- **"Unaccounted" section at bottom**: GroceryItems with zero assigned participants
  - Shown as a special section
  - These items' cost is absorbed by the payer
- **Split recomputation**: any edit to participant assignments is sent to the backend (`PUT /orders/{id}/splits`). Backend recomputes split amounts from original invoice prices — single source of truth for amounts. Client only sends who-gets-what, never amounts.

**Actions:**
- **[Save edits]** → sends edited assignments to backend → backend recomputes → updates split rows
- **[Approve]** → takes finalized split rows as-is, calls `POST /orders/{id}/approve` → backend pushes each split to Splitwise → navigates to Step 3
- **[Back]** → confirmation modal: "Discard this invoice?" → Yes: cancels the draft order (`PATCH /orders/{id}/cancel`), navigates to Home

### Step 3: Split Result (`/invoice/result`)

- Per split group: success ✓ or failure ✗
- Shows basic Splitwise response data (checkmark + key info)
- **[Done / Back to Home]** → navigates to Home

---

## Profile Page (`/profile/[id]`)

- **`/profile/me`** → client-side redirect: frontend reads user ID from auth state and navigates to `/profile/[logged-in-user-id]`
- Accessible by tapping: top-right avatar, any user reference
- **Same page for self and others**, different affordances

### Top section (all users):
- Avatar, name
- Details: email, phone, Splitwise User ID (all read-only, set during onboarding)

### Tabs below profile section:
1. **Meal Plan** tab — their ordered list of MenuItems (names only, read-only for everyone including self — editing is only from Home)
2. **Invoices** tab — past invoices visible for **all** users (not restricted to participants)

### Self-only:
- **Sign out** button
- **Menu Items** tab — MenuItems you own, including archived (shown with "archived" badge). Tappable → MenuItem Detail where user can unarchive. Only shown on your own profile.

---

## Invoices History (Profile → Invoices tab)

- Accessible from **any** user's Profile → Invoices tab
- Shows **all** their past invoices (only `"completed"` orders, not `"draft"` or `"cancelled"`)
- Each entry: date, invoice filename, status, total amount
- Tap to expand/navigate → SPLIT DETAIL
- Split Detail shows **full details** to anyone (even non-participants): extracted items, amounts, classification, split groups, Splitwise audit log
  - **Privacy note**: this is intentional — CartWise is designed for small trusted groups (roommates/friends). All invoice and split data is visible to all signed-in users.
- Backend change: `GET /orders/` needs a variant that lists orders by a specific user (not just "my orders"), and `GET /orders/{id}` must not require participant membership

---

## Meal Plan Visibility

- Your own meal plan is editable from Home (via Meal Plan Edit → Reorder)
- Other users' meal plans are visible **read-only** on their Profile page (Meal Plan tab — names only, not tappable to detail)
- No way to browse other users from Home — you only discover them via profile links or participant search in the wizard

---

## Splitwise User Mapping

- Each CartWise user has a linked Splitwise user ID (integer)
- Configured during **onboarding** — the user enters their Splitwise user ID manually (integer field)
- Stored in `users` table: `splitwise_user_id` integer, NOT NULL (set during onboarding, mandatory)
- Backend migration required
- When creating Splitwise expenses, backend looks up each participant's `splitwise_user_id` from the DB
- The `push_splits_audited()` service builds the `member_id_to_sw_id` mapping from the DB — the frontend does NOT need to provide it
- If a participant somehow has no `splitwise_user_id` (shouldn't happen since onboarding is mandatory) → backend returns error before calling Splitwise

---

## Global Data

- All users fetched on app startup and cached locally
- Used for: participant search, member name + avatar display, profile navigation
- Refreshed on each app launch

---

## API Client & Data Fetching

- **Type generation**: `openapi-typescript` generates TypeScript types (`.d.ts`) from the FastAPI OpenAPI spec (`/openapi.json`)
- **Fetch client**: `openapi-fetch` — 6kb typed fetch client. All API calls are type-checked against the generated schema at compile time.
- **React Query integration**: `openapi-react-query` wraps `openapi-fetch` with TanStack Query hooks (`useQuery`, `useMutation`) for caching, loading states, and mutations.
- **No hand-written API types** — all request/response types come from the generated schema. If the backend changes a Pydantic schema, regenerating the types surfaces every broken call site as a TypeScript error.

### Workflow
```
Backend changes Pydantic schema
  → FastAPI auto-updates /openapi.json
  → `bun run generate:api` regenerates schema.d.ts
  → All fetch calls type-checked against new schema
  → TypeScript errors show exactly what broke
```

### Usage pattern
- **Client Components**: `$api.useQuery("get", "/api/v1/orders/{order_id}", { params: { path: { order_id } } })` — typed path, params, response
- **Server Components**: `client.GET("/api/v1/orders/{order_id}", { params: { path: { order_id } } })` — same client works server-side
- **Mutations**: `$api.useMutation("post", "/api/v1/orders/")` — typed request body, response

### Dependencies
- `openapi-typescript` (devDependency) — CLI that generates `.d.ts` from OpenAPI spec
- `openapi-fetch` — typed fetch client at runtime
- `openapi-react-query` — TanStack Query wrapper for openapi-fetch
- `@tanstack/react-query` — data fetching / caching layer

---

## Currency

- Always INR (₹)

---

## No Offline Support

- App requires network connection
- PWA is for installability and share target only

---

## No Notifications

- No push notifications

---

## Navigation Summary

**No bottom tab bar.** Navigation is:
- **Top bar**: CartWise icon (centre, static) + user avatar (right, → Profile)
- **Home** → Meal Plan Edit / MenuItem Detail / Invoice Wizard / Profile
- **Profile** → MenuItem Detail (self only) / Invoices History / Meal Plan (read-only)
- **Invoice Wizard** → 3-step stepper with dots (Setup → Analysis → Result)
- **Back** → standard browser/OS back button

---

## Screen Map

### Entry Flow

```
APP LAUNCH
  │
  ├── [no Supabase session] → SIGN IN (/login)
  │     └── [Google OAuth success] → Supabase session created
  │           └── call GET /auth/me
  │                 ├── [404 — no DB row] → ONBOARDING (/onboarding)
  │                 │     └── [form submit → POST /auth/onboard] → creates user → HOME (/)
  │                 └── [200 — user exists] → HOME (/)
  │
  └── [Supabase session exists] → call GET /auth/me
        ├── [404] → ONBOARDING (/onboarding)
        └── [200] → HOME (/)
```

### Screen 1: SIGN IN (`/login`)

```
┌─────────────────────────────┐
│        CartWise logo         │
│                              │
│   [Sign in with Google]      │
│                              │
└─────────────────────────────┘

Actions:
  [Sign in with Google] → Supabase OAuth → GET /auth/me → HOME or ONBOARDING
```

### Screen 2: ONBOARDING (`/onboarding`)

```
┌─────────────────────────────┐
│        CartWise logo         │
│    "Welcome! Set up your     │
│         account"             │
│                              │
│  Name: [__________] *        │  ← pre-filled from Google
│  Phone: [__________] *       │  ← 10 digits, freeform
│  Splitwise User ID: [___] *  │  ← integer, mandatory
│                              │
│  [Complete Setup]            │
│                              │
└─────────────────────────────┘

All fields mandatory.
User record is only created in the DB on form submission (POST /auth/onboard).
Once saved → read-only forever.
Close app mid-onboarding → Supabase session persists, form shown again (no re-OAuth).

Actions:
  [Complete Setup] → POST /auth/onboard → creates user in DB → HOME
```

### Screen 3: HOME (`/`)

```
┌─────────────────────────────┐
│      │  [CartWise logo]  │ 😊│  ← top bar (logo centre, avatar right)
├─────────────────────────────┤
│                              │
│  My Meal Plan        [Edit]  │
│                              │
│  ┌──────────────────────┐   │
│  │ Chicken Curry         │   │  ← name only
│  ├──────────────────────┤   │
│  │ Green Salad           │   │
│  └──────────────────────┘   │
│                              │
│  ┌──────────────────────┐   │
│  │   [ New Split ]       │   │  ← CTA, hidden if meal plan empty
│  └──────────────────────┘   │
│                              │
│  --- empty state ---         │
│         [+]                  │  ← plus icon, goes to Meal Plan Edit
│  "No items in your meal      │
│   plan. Tap to add."         │
│                              │
└─────────────────────────────┘

Actions:
  [tap MenuItem row]    → MENUITEM DETAIL (/menu-items/[id])
  [Edit] or [+]         → MEAL PLAN EDIT (/meal-plan/edit)
  [New Split]           → INVOICE SETUP (/invoice) — wizard step 1
  [tap avatar top-right]→ PROFILE (/profile/[my-id])
```

### Screen 4: MEAL PLAN EDIT (`/meal-plan/edit`)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│  Edit Meal Plan              │
│                              │
│  [🔍 Search items...]       │  ← searches heading + body
│  Sort: [Relevance ▾]        │  ← relevance | alphabetical | recently updated | last updated
│                              │
│  ☑ Chicken Curry             │  ← checkbox + name (two tap zones)
│  ☑ Green Salad               │     checkbox toggles, name navigates
│  ☐ Paneer Bhurji             │  ← unchecked = not in plan
│  ☐ Milk Tea                  │
│  ...                         │
│                              │
│  [+ Create New]              │  ← only way to create MenuItems
│                              │
│  [Cancel]        [OK]        │
└─────────────────────────────┘

Only YOUR OWN MenuItems shown. Archived items hidden.
Sort default: "relevance" = checked items first.

Actions:
  [search]              → filters checkbox list (heading + body)
  [sort dropdown]       → re-sorts list
  [tap checkbox]        → toggles item in/out of plan
  [tap item name]       → MENUITEM DETAIL (/menu-items/[id])
  [+ Create New]    → MENUITEM EDITOR (/menu-items/new) → save → back (auto-checked)
  [OK]              → MEAL PLAN REORDER (/meal-plan/reorder)
  [Cancel]          → HOME (/)
```

### Screen 5: MEAL PLAN REORDER (`/meal-plan/reorder`)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│  Reorder Meal Plan           │
│                              │
│  ≡ 1. Chicken Curry     ↕   │  ← drag handle + arrows
│  ≡ 2. Green Salad       ↕   │
│  ≡ 3. Paneer Bhurji     ↕   │
│                              │
│  [Cancel]       [Done]       │
└─────────────────────────────┘

Always shown after Meal Plan Edit OK (even for 1 item).

Actions:
  [drag / arrows]   → reorder items
  [Done]            → saves positions → HOME (/)
  [Cancel]          → discards → HOME (/)
```

### Screen 6: MENUITEM DETAIL (`/menu-items/[id]`)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│                              │
│  Chicken Curry               │  ← headline
│                              │
│  ## Recipe                   │  ← single body, markdown rendered
│  Marinate chicken with       │
│  spices, cook with onions,   │
│  squeeze lemon before        │
│  serving.                    │
│                              │
│  ## Ingredients              │
│  boneless chicken, onion,    │
│  lemon, spices               │
│                              │
│  --- actions ---              │
│  ┌────────┐                  │
│  │ [Edit] │                  │
│  └────────┘                  │
│  ┌──────────────────────┐   │
│  │ [Add to Plan]         │   │  ← switches to [Remove from Plan]
│  └──────────────────────┘   │
│  [Archive] / [Unarchive]     │
│                              │
└─────────────────────────────┘

Actions:
  [Edit]              → MENUITEM EDITOR (/menu-items/[id]/edit) → save → back here
  [Add to Plan]       → MEAL PLAN REORDER → save → back here
  [Remove from Plan]  → confirm → removes → stays here (button switches to Add)
  [Archive/Unarchive] → toggles status
  [← back]            → previous screen
```

### Screen 7: MENUITEM EDITOR (`/menu-items/[id]/edit` or `/menu-items/new`)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│                              │
│  Name:                       │
│  [Chicken Curry          ]   │  ← editable text field
│                              │
│  Body:                       │
│  [                       ]   │  ← single editable text area (markdown)
│  [## Recipe              ]   │     contains recipe + ingredients together
│  [Marinate chicken with  ]   │
│  [spices, cook with...   ]   │
│  [                       ]   │
│  [## Ingredients         ]   │
│  [boneless chicken, onion]   │
│  [                       ]   │
│                              │
│  [Cancel]       [Save]       │
└─────────────────────────────┘

Actions:
  [Save]   → saves → back to MENUITEM DETAIL (or MEAL PLAN EDIT if creating new)
  [Cancel] → discards → back to previous screen
```

### Screen 8: INVOICE SETUP (`/invoice`) — Wizard Step 1

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│         ● ○ ○               │  ← stepper dots (step 1 of 3)
│                              │
│  Upload Invoice              │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│  │      ↑                │  │  ← dashed upload area
│  │  Tap to select PDF    │  │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
│                              │
│  Participants                │
│  [🔍 Search users...]       │
│                              │
│  [You (payer)] [Alice] [Bob] │  ← chips, payer has distinct style
│                              │
│  [Analyse]                   │  ← disabled until file + participants
│                              │
└─────────────────────────────┘

Payer chip: different color/border, non-removable.
Participants cached in localStorage from last session.
Navigate away → "Discard?" confirmation dialog.

Actions:
  [upload area]     → file picker (PDF only)
  [search users]    → dropdown with name + avatar, add on select
  [× on chip]       → remove participant (not payer)
  [Analyse]         → sends to backend → SPLIT ANALYSIS
  [← back]          → "Discard?" → HOME (/)
```

### Screen 9: SPLIT ANALYSIS (`/invoice/review`) — Wizard Step 2

#### View Mode (default)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│         ○ ● ○               │  ← stepper dots (step 2 of 3)
│                              │
│  Split Review    [View|Edit] │  ← toggle
│                              │
│  😊 (Alice)                  │  ← participant avatar only
│  • Chicken Breast            │  ← grocery item names only, no prices
│  • Onion                     │
│  • Lemon                     │
│                              │
│  😊 (Bob)                    │
│  • Cucumber                  │
│  • Cherry Tomato             │
│                              │
│  😊😊😊 (Everyone)            │
│  • Delivery charges          │
│  • Handling charge            │
│                              │
│  [← Back]       [Approve]    │
└─────────────────────────────┘
```

#### Edit Mode

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│         ○ ● ○               │
│                              │
│  Split Review    [View|Edit] │
│                              │
│  Chicken Breast              │  ← grocery item name
│  [😊 Alice ×] [+ add]       │  ← participant chips with name + avatar
│                              │
│  Cucumber                    │
│  [😊 Alice ×] [😊 Bob ×]    │
│  [+ add]                     │
│                              │
│  ── Unaccounted ──           │  ← special section at bottom
│  Yakult Probiotic            │
│  [😊 You (payer)]            │  ← payer as only member
│                              │
│  [← Back]       [Approve]    │
└─────────────────────────────┘

Actions:
  [View|Edit toggle] → switches between view/edit mode
  [× on chip]        → removes participant from item (0 participants → Unaccounted)
  [+ add]            → dropdown to add participant to item
  (any edit)         → triggers client-side split recomputation
  [Approve]          → sends splits to backend → backend calls Splitwise → SPLIT RESULT
  [← Back]           → confirmation modal "Discard?" → Yes: cancels draft order, back to HOME
```

### Screen 10: SPLIT RESULT (`/invoice/result`) — Wizard Step 3

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│         ○ ○ ●               │  ← stepper dots (step 3 of 3)
│                              │
│        ✓ or ✗                │  ← large icon
│  "Splits created!" or        │
│  "Some splits failed"        │
│                              │
│  ✓ ₹315.00 — 2 members      │  ← per-group result
│  ✓ ₹96.00 — 3 members       │
│  ✗ ₹11.00 — failed: ...     │  ← error detail if failed
│                              │
│  [Done → Home]               │
└─────────────────────────────┘

Actions:
  [Done] → HOME (/)
```

### Screen 11: PROFILE (`/profile/[id]`)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│                              │
│         😊                   │  ← large avatar
│      Alice Doe               │  ← name
│                              │
│  Email: alice@gmail.com      │  ← read-only
│  Phone: 9876543210           │  ← read-only
│  Splitwise ID: 12345678      │  ← read-only
│                              │
│  [Sign out]                  │  ← self only
│                              │
│  --- Self profile ---        │
│  ┌────────┬──────────┬────────┐│
│  │MealPlan│ MenuItems│Invoices ││ ← 3 tabs (self)
│  └────────┴──────────┴────────┘│
│                              │
│  --- Others' profile ---     │
│  ┌────────┬────────┐         │
│  │MealPlan│Invoices│          │  ← 2 tabs (others, no Menu Items)
│  └────────┴────────┘         │
│                              │
│  --- Meal Plan tab ---       │
│  1. Chicken Curry            │  ← ordered list, names only, read-only
│  2. Green Salad              │
│                              │
│  --- Menu Items tab (self) --│
│  • Chicken Curry             │  ← items you own, tappable → Detail
│  • Curd Rice                 │
│                              │
│  --- Invoices tab ---        │
│  Apr 12 — invoice.pdf ✓     │  ← past invoices (completed only)
│  ₹1048 — 4 splits           │
│                              │
└─────────────────────────────┘

/profile/me → client-side redirect: reads user ID from auth state, navigates to /profile/[id]

Viewing others' profile:
  - Meal Plan is READ-ONLY (names only, not tappable to detail)
  - Menu Items tab NOT shown
  - Invoices visible to everyone

Actions:
  [tap MenuItem (self)] → MENUITEM DETAIL (/menu-items/[id])
  [tap invoice entry]   → SPLIT DETAIL (/invoices/[id])
  [Sign out] (self)     → clears session → SIGN IN
```

### Screen 12: SPLIT DETAIL (`/invoices/[id]`)

```
┌─────────────────────────────┐
│  ←  │  [CartWise logo]  │ 😊│
├─────────────────────────────┤
│                              │
│  Split — Apr 12, 2026        │
│  invoice.pdf · ₹1048.00     │
│  Status: Completed ✓         │
│                              │
│  ── Extracted Items ──       │
│  Lady Finger · ₹33.00       │
│  Paneer · ₹140.00           │
│  ...                         │
│                              │
│  ── Split Groups ──          │
│  ₹315 → Alice               │
│  ₹96 → Alice, Bob           │
│  ₹11 → Everyone             │
│                              │
│  ── Splitwise Log ──         │
│  ✓ Expense #900001 created   │
│  ✓ Expense #900002 created   │
│                              │
└─────────────────────────────┘

Actions:
  [← back] → PROFILE (Invoices tab)
```

### Complete Navigation Graph

```
                    ┌─────────┐
                    │ SIGN IN │
                    └────┬────┘
                         │ Google OAuth
                    ┌────▼──────┐
                    │ONBOARDING │ (if no user record)
                    └────┬──────┘
                         │ creates user
                    ┌────▼────┐
            ┌───────│  HOME   │───────┐
            │       └────┬────┘       │
            │            │            │
    ┌───────▼──────┐  ┌──▼───┐  ┌────▼────┐
    │MEAL PLAN EDIT│  │DETAIL│  │ INVOICE │
    └───────┬──────┘  │(own) │  │  SETUP  │
            │         └──┬───┘  └────┬────┘
    ┌───────▼───────┐  ┌─▼──┐  ┌────▼─────┐
    │MEAL PLAN      │  │EDIT│  │  SPLIT   │
    │REORDER        │  │    │  │ ANALYSIS │
    └───────┬───────┘  └─┬──┘  └────┬─────┘
            │            │          │
            └─────► HOME ◄──────────┘────► SPLIT RESULT
                    │                          │
              ┌─────▼─────┐                    │
              │  PROFILE   │◄──────────────────┘
              │  (tabbed)  │
              ├────────────┤
              │ MealPlan   │  (read-only names, not tappable)
              │ MenuItems  │──► DETAIL (self only)
              │ Invoices   │──► SPLIT DETAIL (/invoices/[id])
              └────────────┘
```

---

## All Screens

| # | Screen | Route | Type |
|---|---|---|---|
| 1 | Sign In | `/login` | Full page |
| 2 | Onboarding | `/onboarding` | Full page, atomic with sign-in, creates user |
| 3 | Home | `/` | Main screen |
| 4 | Meal Plan Edit | `/meal-plan/edit` | Full page, checkboxes (own items only) |
| 5 | Meal Plan Reorder | `/meal-plan/reorder` | Full page, drag/drop |
| 6 | MenuItem Detail | `/menu-items/[id]` | Full page, markdown viewer (own items only) |
| 7 | MenuItem Editor | `/menu-items/[id]/edit` or `/menu-items/new` | Full page, form (own items only) |
| 8 | Invoice Setup | `/invoice` | Wizard step 1 |
| 9 | Split Analysis | `/invoice/review` | Wizard step 2 |
| 10 | Split Result | `/invoice/result` | Wizard step 3 |
| 11 | Profile | `/profile/[id]` | Full page, tabbed (self: 3 tabs, others: 2 tabs) |
| 12 | Split Detail | `/invoices/[id]` | Full page, past order |

---

## Backend Changes Required

### Database Migrations
1. **`meal_plan_items.position`** — integer column for ordering (migration). Items returned sorted by position.
2. **`users.splitwise_user_id`** — integer column, NOT NULL (set during onboarding). Migration must handle existing rows (add as nullable first, then enforce NOT NULL after backfill or treat as new-only).
3. **MenuItem model** — merge `recipe` + `ingredients` into single `body` text field (migration + code change).

### API Changes
4. **MenuItem `body` field** — rename `recipe`+`ingredients` → `body` in model, schemas (`MenuItemCreate`, `MenuItemUpdate`, `MenuItemResponse`), and all code.
5. **Correlation pipeline** — update `correlate.py` prompt to use the full `body` field instead of just `ingredients`. Update `_snapshot_meal_plans()` to store `body` instead of `ingredients` in the snapshot.
6. **Remove unused menu-item endpoints** — delete `POST /menu-items/{item_id}/fork` route and any related code.
7. **Add unarchive endpoint** — `PATCH /menu-items/{item_id}/unarchive` sets `status = "active"`.
8. **Meal plan set endpoint** — `PUT /meal-plans/me` must accept an ordered list and persist positions. Schema: `{"menu_item_ids": ["uuid1", "uuid2"]}` where order = position. Response returns items sorted by position.
9. **Meal plan response** — `MealPlanResponse.items` must include MenuItem details (at minimum: `menu_item_id`, `name`, `status`, `position`) not just bare IDs.
10. **Order lifecycle** — order status values: `"draft"` (after Analyse) → `"completed"` (after Approve + Splitwise push) | `"cancelled"` (user discards). Change initial status from `"processing"` → `"draft"` in the order pipeline. Change final status from `"completed"` only after Splitwise push succeeds.
11. **Cancel/delete order endpoint** — `DELETE /orders/{order_id}` or `PATCH /orders/{order_id}/cancel` to transition draft orders to `"cancelled"`.
12. **Approve endpoint** — new endpoint that takes an order ID (and optionally edited split assignments), looks up `splitwise_user_id` for each participant from the DB, calls `push_splits_audited()`, and transitions order to `"completed"`. Returns per-group Splitwise results.
13. **Order visibility** — `GET /orders/{order_id}` must NOT require participant membership (anyone can view any completed order). `GET /orders/` needs a `?user_id=` query param to list another user's orders (for Profile → Invoices tab).
14. **Onboarding endpoint** — new `POST /auth/onboard` that creates the user record in the DB with name, phone, splitwise_user_id, and OAuth claims from the JWT. The existing `GET /auth/me` auto-create behavior should be removed — user creation happens only through onboarding.
15. **`/profile/me` redirect** — client-side only. Frontend reads user ID from auth state, navigates to `/profile/[id]`. No backend endpoint needed.
16. **Remove `MenuItemResponse.created_by`/`updated_by` from response** — creator info is implicit (users only see their own). Keep the DB columns but remove from the API response schema. (Or keep them — no harm, just unused.)
17. **Currency** — always `"INR"` everywhere. Backend should pass `currency_code="INR"` explicitly to Splitwise calls.

---

## Open Questions

1. **CTA button label on Home** — TBD. Parked.
