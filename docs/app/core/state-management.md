# State Management

---

## Approach

State is split into two categories with separate tools:

| Category | Tool | Scope |
|---|---|---|
| Server state | TanStack Query | Remote data, caching, background refetch |
| Client state | Zustand | Auth session, persisted UI state |

There is no global Redux store. Local component state handles everything that does not need to be shared.

---

## Server state with TanStack Query

All API data lives in TanStack Query. Queries fetch and cache remote data. Mutations write to the server and invalidate related queries.

Queries are colocated with the feature that owns them, under `features/<name>/hooks/`:

```
features/
  events/
    hooks/
      useEvents.ts
      useEvent.ts
  tickets/
    hooks/
      useTickets.ts
      useCreateReservation.ts
```

### Writing a query

```ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useEvent(eventId: string) {
  return useQuery({
    queryKey: ['events', eventId],
    queryFn: () => api.get(`/catalog/v1/events/${eventId}`).json(),
    enabled: !!eventId,
  })
}
```

### Writing a mutation

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useCreateReservation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => api.post('/sales/v1/reservations', { json: data }).json(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reservations'] }),
  })
}
```

### Query key conventions

Keys are arrays that go from general to specific:

```ts
['events']               // all events
['events', eventId]      // single event
['events', eventId, 'ticket-types']  // ticket types for an event
```

---

## Client state with Zustand

Zustand stores handle state that is not tied to a remote resource. Currently there is one store:

### Auth store

File: `src/store/auth.ts`

Holds the active session tokens. Persisted to `localStorage` so the user stays logged in across page reloads.

```ts
import { useAuthStore } from '@/store/auth'

const { isAuthenticated, clearSession } = useAuthStore()
```

Key fields:

| Field | Purpose |
|---|---|
| `isAuthenticated` | Whether the user has an active session |
| `accessToken` | JWT for API calls |
| `refreshToken` | Token used to obtain new access tokens |
| `isSetupPending` | User registered but setup is not complete |
| `isTotpPending` | TOTP challenge is in progress |

The store uses `immer` middleware for immutable updates and `persist` middleware for localStorage serialisation.

### Adding a new store

Create a file in `src/store/`. Use `create` from zustand with `immer` middleware if the state has nested updates.

Only use Zustand for state that:
- Does not come from the API
- Needs to be accessed in multiple unrelated components
- Needs to survive navigation

For anything else, prefer local state or TanStack Query.

---

## Local state

Use `useState` and `useReducer` for state that is local to a component or a small section of the UI: form field values, toggle states, modal visibility.

Do not lift local state into a global store just because it feels neater.

---

## Derived state

Compute derived values inline where they are used. Do not cache derived state in a store or query unless the computation is expensive.

```ts
const { data: event } = useEvent(eventId)
const isEditable = event?.status === 'draft' || event?.status === 'published'
```
