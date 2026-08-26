# Qrew — Frontend Development Plan

This document maps every backend capability to a UI development phase.
Each phase becomes one or more GitHub issues.

---

## Current state

| Feature | Status |
|---|---|
| Register | ✅ Done |
| Login | ✅ Done |
| Everything else | ⬜ Not started |

---

## Phase 1 — Identity: Onboarding flow

After login, if `setup_required: true` the backend issues a **setup JWT** (not a regular access token).
The user must complete all steps before they can use the app. The backend enforces this at the token level.

**Steps (in order):**
1. Verify email — `POST /v1/auth/registration/verify-email` (token from email)
2. Verify phone — `POST /v1/auth/registration/verify-phone` (OTP via SMS)
3. Upload KYC document — `POST /v1/auth/setup/kyc/upload` (national ID scan)
4. Complete setup — `POST /v1/auth/setup/complete-setup`

**UI needed:**
- Detect `setup_required` in login response → redirect to `/setup`
- Step-by-step onboarding wizard with progress indicator
- Email verification: enter token from email (or handle magic link)
- Phone verification: OTP input with resend
- KYC upload: file/camera input, upload via signed URL (`POST /v1/auth/uploads/sign`)
- Completion screen → redirect to app

**Notes:**
- KYC has states: `not_submitted` → `pending` → `approved` / `rejected`
- `pending` state needs a waiting screen ("we're reviewing your ID")
- `rejected` needs a retry flow
- All setup endpoints require the setup token, not the access token — store separately

**Issue:** `QRW-247 — Implement post-login onboarding flow`

---

## Phase 2 — Identity: Profile & account management

**UI needed:**
- `/profile` — view name, email, phone, KYC status, account created date
- Change password — `POST /v1/auth/change-password`
- Change email — `POST /v1/auth/change-email` + confirm via token
- Change phone — `POST /v1/auth/change-phone` + confirm via OTP
- Active sessions list — revoke individual or all (`DELETE /v1/auth/sessions/{jti}`, `POST /v1/auth/sessions/revoke-all`)
- Delete account — `POST /v1/auth/delete` (with confirmation dialog)
- Onboarding status widget — shows which steps are complete

**Issue:** `QRW-248 — Implement profile and account management`

---

## Phase 3 — Identity: Passkeys

Full WebAuthn flow. Optional but enhances security and UX significantly.

**UI needed:**
- Register passkey button in profile/security settings
- Passkey list with rename/delete
- Passkey login option on login page (alongside email+password)

**Endpoints:** `POST /v1/auth/passkey/register/begin|complete`, `POST /v1/auth/passkey/authenticate/begin|complete`, `GET /v1/auth/passkey/`, `DELETE /v1/auth/passkey/{id}`, `PATCH /v1/auth/passkey/{id}`

**Issue:** `QRW-249 — Implement passkey registration and authentication`

---

## Phase 4 — Catalog: Events discovery

First feature outside identity. Requires catalog service running.

**UI needed:**
- `/events` — searchable, filterable event listing (`GET /v1/events/search`)
- `/events/{id}` — event detail page with description, date, venue, ticket types + availability
- Ticket type cards showing price, availability, per-person limits
- Availability indicator (sold out, limited, available) from `GET /v1/events/{id}/availability`

**Notes:**
- Events have a `published` state — only published events appear in public search
- Ticket types can be capacity-limited

**Issue:** `QRW-250 — Implement events discovery and detail pages`

---

## Phase 5 — Catalog: Organisation management

Organiser-side flows. Users with organiser role can create organisations and events.

**UI needed:**
- `/organisations/new` — create organisation
- `/organisations/{id}` — org dashboard: members, events list
- Add/remove members
- `/organisations/{id}/events/new` — create event form (name, description, venue, dates, capacity)
- Publish / cancel event actions
- Ticket type management (create, edit, delete) per event

**Issue:** `QRW-251 — Implement organisation and event management`

---

## Phase 6 — Purchase flow: Queue → Reservation → Payment

Core transactional flow. Three services involved (sales, payments, ticketing).

**Step 1 — Queue (for high-demand events):**
- Join queue button on event detail — `POST /v1/events/{id}/queue/join`
- Queue position page — poll `GET /v1/events/{id}/queue/position`
- When position reached → redeem slot — `POST /v1/events/{id}/queue/redeem` → creates reservation
- Real-time position updates via WebSocket (Phase 8)

**Step 2 — Reservation:**
- Reservation summary page showing ticket type, quantity, price, expiry countdown
- Cancel reservation option — `POST /v1/events/{id}/reservations/{id}/cancel`
- Reservations expire (TTL ~10 min) — show countdown timer

**Step 3 — Payment:**
- Initiate payment — `POST /v1/reservations/{id}/payment` → returns Stripe client secret
- Stripe payment UI (Stripe Elements)
- Payment confirmation → ticket issued

**Notes:**
- KYC must be `approved` before purchase is allowed (backend enforces)
- Reservation has a hard expiry — if timer runs out, user must re-queue

**Issue:** `QRW-252 — Implement queue, reservation, and payment flow`

---

## Phase 7 — My Tickets

**UI needed:**
- `/tickets` — list of user's tickets with event name, date, status
- `/tickets/{id}` — ticket detail with rotating QR code
- QR refreshes automatically (stream from `POST /v1/tickets/{id}/qr/stream` via SSE)
- Ticket states shown clearly: `reserved` / `issued` / `used` / `cancelled` / `frozen` / `flagged`

**Issue:** `QRW-253 — Implement my tickets and QR code display`

---

## Phase 8 — Real-time: WebSocket integration

Gateway exposes `WS /ws/{channel_key}` — JWT authenticated, pushes live NATS events to browser.

**Use cases:**
- Queue position updates (Phase 6)
- Ticket state changes
- Entry stats for organisers (Phase 9)

**UI needed:**
- WebSocket client hook (`useWebSocket`) with auto-reconnect
- Channel subscription by key
- Wire into queue position and organiser stats pages

**Issue:** `QRW-254 — Implement WebSocket real-time client`

---

## Phase 9 — Organiser: Entry dashboard

For event organisers to monitor door entry in real time.

**UI needed:**
- `/events/{id}/entry` — live entry stats dashboard
- Total issued / entered / remaining
- Rejection reason breakdown
- Real-time updates via WebSocket

**Endpoints:** `GET /v1/events/{id}/entry-stats` (entry service)

**Issue:** `QRW-255 — Implement organiser entry stats dashboard`

---

## Phase 10 — Scanner app

Separate authenticated flow for door scanners. Uses scanner JWT (not user JWT).

**UI needed:**
- Scanner login / token refresh — `POST /v1/scanner/refresh`
- QR scan interface (camera, barcode reader)
- Submit scan — `POST /v1/entry/validate`
- Result display: green (admit) / red (reject) with rejection reason
- Optimised for tablet/kiosk use

**Issue:** `QRW-256 — Implement scanner validation app`

---

## Suggested issue creation order

| Priority | Issue | Depends on |
|---|---|---|
| 1 | QRW-247 Onboarding flow | Auth (done) |
| 2 | QRW-248 Profile & account | Auth (done) |
| 3 | QRW-250 Events discovery | — |
| 4 | QRW-251 Organisation management | Events |
| 5 | QRW-252 Purchase flow | Events + KYC |
| 6 | QRW-253 My tickets | Purchase flow |
| 7 | QRW-254 WebSocket client | — |
| 8 | QRW-255 Entry dashboard | WebSocket |
| 9 | QRW-249 Passkeys | Profile |
| 10 | QRW-256 Scanner app | — |

---

## Services required per phase

| Phase | Services needed locally |
|---|---|
| 1–3 (identity) | `just identity-dev` |
| 4–5 (catalog) | `just identity-dev` + `just catalog-dev` |
| 6 (purchase) | identity + catalog + `just sales-dev` + `just payments-dev` + `just ticketing-dev` |
| 7 (tickets) | identity + ticketing |
| 8 (realtime) | `just gateway-dev` |
| 9 (entry) | identity + `just entry-dev` |
| 10 (scanner) | identity + entry + ticketing |
