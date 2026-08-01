# Routing

The app uses TanStack Router with file-based routing. Routes live in `src/routes/`.


## Route Tree

```
src/routes/
  __root.tsx              Root layout (QueryClient, i18n, Toaster)
  _app.tsx                Authenticated layout (BottomDock, auth guard)
  _app/
    home/
      index.tsx           Home feed
    events/
      index.tsx           Event listing
      $eventId/
        index.tsx         Event detail
        checkout.tsx      Ticket selection and checkout
        queue.tsx         Queue waiting room
    tickets/
      index.tsx           My tickets
      $ticketId.tsx       Ticket detail + QR code
    reservations/
      $reservationId/
        index.tsx         Reservation checkout (holder info + payment)
    market/
      index.tsx           Market hub
      listing/$listingId  Listing detail
      assignment/$id      Assignment detail (pending claim)
    profile/
      index.tsx           Profile overview
      edit.tsx            Edit profile
      security.tsx        Security log, sessions
    management/
      index.tsx           Organisation list
      new.tsx             Create organisation
      $orgId/
        index.tsx         Organisation detail
        events/
          $eventId/
            index.tsx     Event management overview
            edit.tsx      Edit event
            tickets.tsx   Manage ticket types
            scan.tsx      QR scanner
            stats.tsx     Entry stats
  _auth.tsx               Unauthenticated layout
  _auth/
    login.tsx
    register/
      index.tsx
      verify.tsx          Phone OTP verification
      kyc.tsx             KYC document upload
    setup.tsx             Passkey registration (post-registration)
    forgot-password.tsx
    reset-password.tsx
  $.tsx                   404 catch-all
```


## Layouts and Guards

### `__root.tsx`

The root layout wraps everything. It provides the `QueryClientProvider`, `I18nextProvider`, and `Toaster`. No auth logic here.

### `_app.tsx`

All routes under `_app/` require the user to be authenticated. The layout's `beforeLoad` hook reads the auth store. If no valid session exists, it redirects to `/login`. It also renders the `BottomDock` navigation.

### `_auth.tsx`

Routes for unauthenticated users (login, register, password reset). If an authenticated user lands here, they are redirected to `/home`.


## Auth Flow

1. User visits any `_app/` route without a session → redirected to `/login`
2. After login, the app stores the access token in memory via Zustand and the refresh token in `@capacitor/preferences`. On mobile this uses native secure storage. On web it falls back to localStorage.
3. Axios interceptor attaches `Authorization: Bearer <token>` to every request
4. On 401, the interceptor silently refreshes the access token using the refresh token, then retries the original request
5. On refresh failure, the user is signed out and redirected to `/login`


## Navigation

The app uses `<Link>` and `useNavigate()` from TanStack Router. Never use `<a href>` for internal links.

The `BottomDock` drives top-level navigation between Home, Events, Tickets, Market, and Profile. Management routes are accessible from the Profile tab for org members.


## Route Parameters

| Parameter | Type | Description |
|---|---|---|
| `$eventId` | UUID | Event identifier |
| `$ticketId` | UUID | Ticket identifier |
| `$reservationId` | UUID | Reservation identifier |
| `$orgId` | UUID | Organisation identifier |
| `$listingId` | UUID | Market listing identifier |


## Search Parameters

Some routes use validated search params via Zod schemas:

| Route | Param | Purpose |
|---|---|---|
| `checkout.tsx` | `reservation_window_token` | Queue admission token |
| `checkout.tsx` | `admitted` | Whether user was admitted from queue |
| `reset-password.tsx` | `token` | Password reset token from email |
