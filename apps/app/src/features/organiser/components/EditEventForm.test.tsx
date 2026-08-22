import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { type OrgEvent } from '../api'
import { EditEventForm } from './EditEventForm'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const CATALOG = 'http://localhost:8000/api/catalog'

const EVENT: OrgEvent = {
  id: 'event-1',
  organisation_id: 'org-1',
  venue_id: 'venue-1',
  name: 'Summer Fest',
  description: 'An outdoor festival',
  image_url: null,
  starts_at: '2026-08-15T20:00:00Z',
  ends_at: '2026-08-15T23:00:00Z',
  sale_starts_at: '2026-07-01T10:00:00Z',
  sale_ends_at: '2026-08-14T23:00:00Z',
  max_tickets_per_user: 4,
  status: 'draft',
  started_at: null,
  organiser_name: 'Qrew Events',
  venue_city: 'Barcelona',
  queue_required: false,
  created_at: '2026-06-01T00:00:00Z',
  published_at: null,
  cancelled_at: null,
}

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <EditEventForm event={EVENT} orgId="org-1" />
    </QueryClientProvider>,
  )
}

describe('EditEventForm', () => {
  it('arrives filled with what the event already says', async () => {
    renderForm()
    expect(screen.getByLabelText(/^name$/i)).toHaveValue('Summer Fest')
    expect(screen.getByLabelText(/description/i)).toHaveValue('An outdoor festival')
    expect(screen.getByLabelText(/max tickets/i)).toHaveValue(4)
  })

  it('offers the venues the organisation has', async () => {
    renderForm()
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /palau sant jordi/i })).toBeInTheDocument()
    })
  })

  it('sends the change when the name is edited', async () => {
    let received: Record<string, unknown> | null = null
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId`, async ({ request }) => {
        received = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ ...EVENT, name: 'Winter Fest' })
      }),
    )
    renderForm()
    const name = screen.getByLabelText(/^name$/i)
    await userEvent.clear(name)
    await userEvent.type(name, 'Winter Fest')
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => expect(received).not.toBeNull())
    expect(received!.name).toBe('Winter Fest')
  })

  it('refuses to send an event without a name', async () => {
    let calls = 0
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId`, () => {
        calls += 1
        return HttpResponse.json(EVENT)
      }),
    )
    renderForm()
    await userEvent.clear(screen.getByLabelText(/^name$/i))
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => expect(screen.getByLabelText(/^name$/i)).toHaveValue(''))
    expect(calls).toBe(0)
  })

  it('reports the rejection when the server refuses the change', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId`, () =>
        HttpResponse.json({ detail: { message: 'Sale window is invalid' } }, { status: 409 }),
      ),
    )
    renderForm()
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
  })
})
