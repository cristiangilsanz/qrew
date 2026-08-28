// tests cancel event section
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { type OrgEvent } from '../api'
import { CancelEventSection } from './CancelEventSection'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const CATALOG = 'http://localhost:8000/api/catalog'

const EVENT = {
  id: 'event-1',
  organisation_id: 'org-1',
  venue_id: 'venue-1',
  name: 'Summer Fest',
  description: null,
  image_url: null,
  starts_at: '2026-08-15T20:00:00Z',
  ends_at: '2026-08-15T23:00:00Z',
  sale_starts_at: '2026-07-01T10:00:00Z',
  sale_ends_at: '2026-08-14T23:00:00Z',
  max_tickets_per_user: 4,
  status: 'published',
  started_at: null,
  organiser_name: 'Qrew Events',
  venue_city: 'Barcelona',
  queue_required: false,
  created_at: '2026-06-01T00:00:00Z',
  published_at: '2026-07-01T00:00:00Z',
  cancelled_at: null,
} as OrgEvent

// implements render section
function renderSection() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <CancelEventSection event={EVENT} orgId="org-1" />
    </QueryClientProvider>,
  )
}

// implements open and wait out the delay
async function openAndWaitOutTheDelay() {
  await userEvent.click(screen.getByRole('button', { name: /cancel event/i }))
  for (let tick = 0; tick < 6; tick += 1) {
    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
  }
}

describe('CancelEventSection', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows only the entry button until it is pressed', () => {
    renderSection()
    expect(screen.getByRole('button', { name: /cancel event/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /go back/i })).not.toBeInTheDocument()
  })

  it('holds the confirmation back while the countdown runs', async () => {
    renderSection()
    await userEvent.click(screen.getByRole('button', { name: /cancel event/i }))
    expect(screen.getByRole('button', { name: /wait/i })).toBeDisabled()
  })

  it('cancels the event once the countdown ends', async () => {
    let calls = 0
    server.use(
      http.post(`${CATALOG}/v1/events/:eventId/cancel`, () => {
        calls += 1
        return HttpResponse.json({ ...EVENT, status: 'cancelled' })
      }),
    )
    renderSection()
    await openAndWaitOutTheDelay()
    await userEvent.click(screen.getAllByRole('button', { name: /cancel event/i })[1]!)
    await waitFor(() => expect(calls).toBe(1))
  })

  it('sends nothing when the user goes back', async () => {
    let calls = 0
    server.use(
      http.post(`${CATALOG}/v1/events/:eventId/cancel`, () => {
        calls += 1
        return HttpResponse.json(EVENT)
      }),
    )
    renderSection()
    await openAndWaitOutTheDelay()
    await userEvent.click(screen.getByRole('button', { name: /go back/i }))
    await act(async () => {
      vi.advanceTimersByTime(500)
    })
    expect(calls).toBe(0)
  })

  it('reports the rejection when the event cannot be cancelled', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post(`${CATALOG}/v1/events/:eventId/cancel`, () =>
        HttpResponse.json({ detail: { message: 'Event already started' } }, { status: 409 }),
      ),
    )
    renderSection()
    await openAndWaitOutTheDelay()
    await userEvent.click(screen.getAllByRole('button', { name: /cancel event/i })[1]!)
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
  })
})
