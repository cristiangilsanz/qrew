# App

## Introduction

This document is the developer reference for the frontend application.

1. [Layout](#layout)
2. [Routing](#routing)
3. [Components](#components)
4. [State Management](#state-management)
5. [Data Fetching](#data-fetching)
6. [i18n](#i18n)
7. [Native Integration](#native-integration)

## Layout

All source code lives under `apps/app/src/`, organised by concern at the top level:

```
src/
  routes/        Route definitions
  features/      Feature modules
  components/    Shared UI primitives
  hooks/         Shared hooks
  i18n/          Translations
  store/         Global state
  lib/           Utilities and helpers
  config/        App configuration
  assets/        Static assets
  styles/        Global styles
  test/          Test setup
```

Each feature lives under `src/features/<name>/` and owns its own components, hooks, and types:

```
features/<name>/
  components/    UI specific to this feature
  hooks/         Queries, mutations, and local logic
  types.ts       Types for this feature
```
Nothing outside the feature should import from it except routes.

## Routing

The app uses TanStack Router with file-based routing and it is fully type-safe end to end:

```
src/routes/
├── index.tsx                                     (Redirect to /home)
├── confirm-email-change.tsx
├── __root.tsx                                    Root Layout (QueryClient, i18n, Toaster)
├── _app.tsx                                      Authenticated Layout
├── _app/
│   ├── $.tsx                                     404
│   ├── home/index.tsx
│   ├── events/
│   │   ├── index.tsx
│   │   └── $eventId/
│   │       ├── index.tsx
│   │       ├── checkout.tsx
│   │       └── queue.tsx
│   ├── tickets/
│   │   ├── index.tsx
│   │   └── $ticketId.tsx
│   ├── reservations/$reservationId/index.tsx
│   ├── market/
│   │   ├── index.tsx
│   │   ├── offers/
│   │   │   ├── index.tsx
│   │   │   └── $offerId/
│   │   │       ├── index.tsx
│   │   │       └── checkout.tsx
│   │   ├── on-sale/index.tsx
│   │   └── waitlists/index.tsx
│   ├── profile/
│   │   ├── index.tsx
│   │   ├── account.tsx
│   │   ├── security.tsx
│   │   ├── passkeys.tsx
│   │   ├── recover-device.tsx
│   │   ├── privacy.tsx
│   │   ├── terms.tsx
│   │   ├── about.tsx
│   │   └── help.tsx
│   ├── management.tsx                            Management layout
│   └── management/
│       ├── index.tsx
│       ├── new.tsx
│       └── $orgId/
│           ├── index.tsx
│           ├── events/
│           │   ├── index.tsx
│           │   ├── new.tsx
│           │   └── $eventId/
│           │       ├── index.tsx
│           │       ├── edit.tsx
│           │       ├── tickets.tsx
│           │       ├── scan.tsx
│           │       └── stats.tsx
│           ├── collaborators/
│           │   ├── index.tsx
│           │   └── new.tsx
│           └── venues/new.tsx
├── _auth.tsx                                     Unauthenticated layout
└── _auth/
    ├── login.tsx
    ├── register.tsx
    ├── setup.tsx
    ├── verify-email.tsx
    ├── verify-totp.tsx
    ├── forgot-password.tsx
    └── reset-password.tsx
```

On an unauthenticated visit to any `_app/` route the router redirects to `/login`. The gateway allows an account that has not finished verification to read but not to write, so until then the app keeps it on the setup wizard for anything beyond browsing. After login, the access token is stored in Zustand and the refresh token in `@capacitor/preferences`. An Axios interceptor attaches `Authorization: Bearer <token>` to every request and silently refreshes it on 401 before retrying.

## Components

The UI kit is a set of components built on Radix UI primitives and styled with Tailwind, with shared components living in `src/components/ui/` and anything specific to a feature staying inside it.

### Design System

Files in `src/components/ui/`:

| Component | Description |
|---|---|
| `BackButton` | Navigate back |
| `Badge` | Status label |
| `Button` | Action button |
| `Card` | Surface container |
| `ConfirmDialog` | Confirmation dialog |
| `Dialog` | Modal dialog |
| `EmptyState` | Empty list message |
| `Form` | Form wrapper |
| `ImageWithSkeleton` | Image with loading skeleton |
| `Input` | Text input |
| `NotFound` | Not found message |
| `PageHeader` | Page title and subtitle |
| `Skeleton` | Loading placeholder |
| `StatusChip` | Status chip |

### Conventions

<dl>
<dt>• <strong><em>Naming.</em></strong></dt>
<dd>Components are PascalCase. Hooks are prefixed with <code>use</code>. Files match the name of their default export.</dd>
<dt>• <strong><em>Styling.</em></strong></dt>
<dd>Use Tailwind utility classes only. Merge conditionals with <code>cn()</code> from <code>src/lib/utils.ts</code>. No inline styles.</dd>
<dt>• <strong><em>Loading states.</em></strong></dt>
<dd>Use <code>Skeleton</code> in dedicated skeleton layouts. Always use <code>ImageWithSkeleton</code> instead of a plain <code>&lt;img&gt;</code>.</dd>
<dt>• <strong><em>Error states.</em></strong></dt>
<dd>Use the shared <code>EmptyState</code> and <code>NotFound</code> components.</dd>
<dt>• <strong><em>Testing.</em></strong></dt>
<dd>Every component in <code>src/components/ui/</code> should have a colocated <code>*.test.tsx</code> file.</dd>
</dl>

## State Management

The app splits state into two clear categories:

| Category | Tool |
|---|---|
| Client state | Zustand |
| Server state | TanStack Query |

> [!NOTE]
> Use Zustand only for state that does not come from the API, needs to be shared across unrelated components, or must survive navigation. For everything else, prefer `useState` or TanStack Query.

Accessing the auth store as an example:

```ts
import { useAuthStore } from '@/store/auth'

const { isAuthenticated, clearSession } = useAuthStore()
```

## Data Fetching

All server communication goes through TanStack Query, which handles caching, background refetching, and loading/error states.

Queries and mutations live under `features/<name>/hooks/` and follow this pattern:

```ts
// Query
export function useEvent(eventId: string) {
  return useQuery({
    queryKey: ['events', eventId],
    queryFn: () => api.get(`/catalog/v1/events/${eventId}`).then(r => r.data),
    enabled: !!eventId,
  })
}

// Mutation
export function useCreateReservation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => api.post('/sales/v1/reservations', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reservations'] }),
  })
}
```

Query keys identify cached data and control invalidation. They are arrays ordered from general to specific — invalidating a prefix clears everything beneath it. Invalidating `['events']` wipes all event queries; invalidating `['events', eventId]` wipes only that one event. A consistent naming pattern across the codebase:

```ts
['events']                           // fetches all events
['events', eventId]                  // fetches a single event by id
['events', eventId, 'ticket-types']  // fetches ticket types for that event
```

## i18n

All user-visible text is managed with react-i18next. Supported languages are English (`en`) and Spanish (`es`), with the active language persisted under `qrew_lang` in `localStorage`.

> [!NOTE]
> Never hardcode user-visible text in JSX. All strings must live in the locale files.

Use the `t()` hook to access translations:

```tsx
import { useTranslation } from 'react-i18next'

const { t } = useTranslation()
return <h1>{t('events.title')}</h1>
```

To add a new string, add the key and value to both `src/i18n/locales/en.json` and `src/i18n/locales/es.json`, then use it via `t('your.key')`. To add a new language, create `src/i18n/locales/<code>.json` with all keys translated and register it in `src/i18n/index.ts`.

## Native Integration

Capacitor wraps the React app in a native shell, giving it access to device APIs (camera, GPS, haptics, push notifications, etc.), while keeping a single codebase for Android, iOS, and the browser.

The following plugins are used to access device capabilities:

| Plugin | |
|---|---|
| `@capacitor/camera` | Camera access |
| `@capacitor/geolocation` | GPS location |
| `@capacitor/haptics` | Vibration |
| `@capacitor/keyboard` | Keyboard insets |
| `@capacitor/network` | Network status |
| `@capacitor/preferences` | Key-value storage |
| `@capacitor/push-notifications` | Push notifications |
| `@capacitor/splash-screen` | Splash screen |
| `@capacitor/status-bar` | Status bar |
| `@capawesome/capacitor-passkeys` | Passkey auth |

All native calls are guarded so the app degrades gracefully in the browser:

```ts
if (Capacitor.isNativePlatform()) {
  await Haptics.vibrate()
}
```
