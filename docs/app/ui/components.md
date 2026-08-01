# Components

Components live in two places:

- `src/components/` for shared, domain-agnostic UI
- `src/features/<name>/components/` for domain components used only within that feature


## Design System

Files live in `src/components/ui/`.

These are the building blocks used throughout the app.

| Component | File | Description |
|---|---|---|
| `BackButton` | `back-button.tsx` | Icon button for navigating back |
| `Badge` | `badge.tsx` | Small status label with variants |
| `Button` | `button.tsx` | Primary action button, Radix Slot-based |
| `Card` | `card.tsx` | Surface container with padding |
| `ConfirmDialog` | `confirm-dialog.tsx` | Modal confirmation with cancel/confirm |
| `Dialog` | `dialog.tsx` | Radix dialog wrapper |
| `EmptyState` | `empty-state.tsx` | Centred message for empty lists |
| `Form` | `form.tsx` | React Hook Form + Radix Label wrappers |
| `ImageWithSkeleton` | `image-with-skeleton.tsx` | Image that shows a skeleton until loaded or errored |
| `Input` | `input.tsx` | Text input with consistent styling |
| `Label` | `label.tsx` | Radix Label wrapper |
| `NotFound` | `not-found.tsx` | Centred message for missing resources, optional action |
| `PageHeader` | `page-header.tsx` | Title + optional subtitle for page tops |
| `Skeleton` | `skeleton.tsx` | Animated placeholder shapes for loading states |
| `StatusChip` | `status-chip.tsx` | Coloured chip for event/ticket status values |
| `Tooltip` | radix-ui | Hover tooltip via Radix UI |


## Layout Components

Files live in `src/components/layout/`.

| Component | File | Description |
|---|---|---|
| `BottomDock` | `BottomDock.tsx` | Fixed bottom navigation bar with 5 tabs |


## Conventions

### Styling

All styling uses Tailwind CSS utility classes. Use the `cn()` helper from `src/lib/utils.ts` to merge conditional classes:

```tsx
import { cn } from '@/lib/utils'

<div className={cn('base-class', isActive && 'active-class')} />
```

Do not use inline styles or CSS modules.

### Variants

Components that have multiple visual states use a `variant` or `status` prop. The `StatusChip` component maps event and ticket status strings to colour variants automatically.

### Empty and Not-Found States

Use the shared components rather than inline patterns:

```tsx
import { EmptyState } from '@/components/ui/empty-state'
import { NotFound } from '@/components/ui/not-found'

// For empty lists
<EmptyState message={t('tickets.empty')} />

// For missing resources
<NotFound
  message={t('events.notFound')}
  action={{ label: t('events.browse'), to: '/events' }}
/>
```

### Loading States

Use `Skeleton` components in dedicated skeleton layouts such as `EventSkeleton` and `TicketSkeleton`, defined in `src/components/ui/skeleton.tsx`. Each major page has its own skeleton that matches the page layout.

For images, always use `ImageWithSkeleton` instead of a plain `<img>`. It shows the skeleton until the image loads and handles errors silently.

### Testing

Every component in `src/components/ui/` should have a corresponding test file (`*.test.tsx`). Tests use Vitest and React Testing Library. Keep tests focused on rendering and visible output. Not implementation details.

```tsx
import { render, screen } from '@testing-library/react'
import { StatusChip } from './status-chip'

it('renders the status label', () => {
  render(<StatusChip status="published" />)
  expect(screen.getByText('Published')).toBeInTheDocument()
})
```


## Feature Components

Feature components live in `src/features/<name>/components/` and are only imported within their own feature or from routes. They can use domain types and API hooks directly.

Examples:

| Feature | Component | Description |
|---|---|---|
| `organiser` | `EventActions` | Floating action button for publish/start/scan |
| `organiser` | `CreateEventForm` | Multi-field form for creating events |
| `organiser` | `CreateVenueForm` | Form with Google Maps place search |
| `tickets` | `StripeCheckout` | Lazy-loaded Stripe Elements payment form |
| `scanner` | `QrScanner` | Capacitor camera-based QR scanner |


## Radix UI Primitives

Low-level accessible primitives (Dialog, DropdownMenu, Tooltip, Label, Slot) come from `@radix-ui/*` packages. Use the existing wrappers in `src/components/ui/` rather than consuming Radix directly in feature or route files.
