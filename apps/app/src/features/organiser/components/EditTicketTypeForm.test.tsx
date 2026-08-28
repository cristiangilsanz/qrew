// tests edit ticket type form
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { CapacityEditTicketTypeForm, EditTicketTypeForm } from './EditTicketTypeForm'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const CATALOG = 'http://localhost:8000/api/catalog'

const DEFAULTS = {
  name: 'general_admission',
  description: 'Standing area',
  capacity: 100,
  price_cents: 25,
  position: 0,
}

// implements render edit
function renderEdit(onClose = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <EditTicketTypeForm
        ttId="tt-1"
        eventId="event-1"
        defaultValues={DEFAULTS}
        onClose={onClose}
      />
    </QueryClientProvider>,
  )
  return onClose
}

// implements render capacity
function renderCapacity(onClose = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <CapacityEditTicketTypeForm
        ttId="tt-1"
        eventId="event-1"
        currentCapacity={80}
        onClose={onClose}
      />
    </QueryClientProvider>,
  )
  return onClose
}

describe('EditTicketTypeForm', () => {
  it('arrives filled with what the ticket type already says', () => {
    renderEdit()
    expect(screen.getByLabelText(/name/i)).toHaveValue('general_admission')
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(100)
  })

  it('sends the change and closes itself', async () => {
    let received: Record<string, unknown> | null = null
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId/ticket-types/:ttId`, async ({ request }) => {
        received = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 'tt-1' })
      }),
    )
    const onClose = renderEdit()
    const capacity = screen.getByLabelText(/capacity/i)
    await userEvent.clear(capacity)
    await userEvent.type(capacity, '250')
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => expect(onClose).toHaveBeenCalled())
    await waitFor(() => expect(received).not.toBeNull())
    expect(received!.capacity).toBe(250)
  })

  it('turns the price into cents before sending it', async () => {
    let received: Record<string, unknown> | null = null
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId/ticket-types/:ttId`, async ({ request }) => {
        received = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 'tt-1' })
      }),
    )
    renderEdit()
    const price = screen.getByLabelText(/price/i)
    await userEvent.clear(price)
    await userEvent.type(price, '12.50')
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => expect(received).not.toBeNull())
    expect(received!.price_cents).toBe(1250)
  })

  it('refuses a name with spaces', async () => {
    let calls = 0
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId/ticket-types/:ttId`, () => {
        calls += 1
        return HttpResponse.json({ id: 'tt-1' })
      }),
    )
    renderEdit()
    const name = screen.getByLabelText(/name/i)
    await userEvent.clear(name)
    await userEvent.type(name, 'general admission')
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => {
      expect(screen.getByText(/must start with a letter/i)).toBeInTheDocument()
    })
    expect(calls).toBe(0)
  })

  it('closes without sending when the user cancels', async () => {
    const onClose = renderEdit()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })
})

describe('CapacityEditTicketTypeForm', () => {
  it('arrives with the capacity the type has', () => {
    renderCapacity()
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(80)
  })

  it('sends only the capacity', async () => {
    let received: Record<string, unknown> | null = null
    server.use(
      http.patch(`${CATALOG}/v1/events/:eventId/ticket-types/:ttId`, async ({ request }) => {
        received = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 'tt-1' })
      }),
    )
    renderCapacity()
    const capacity = screen.getByLabelText(/capacity/i)
    await userEvent.clear(capacity)
    await userEvent.type(capacity, '120')
    await userEvent.click(screen.getByRole('button', { name: /^update$/i }))
    await waitFor(() => expect(received).not.toBeNull())
    expect(received).toEqual({ capacity: 120 })
  })

  it('closes without sending when the user cancels', async () => {
    const onClose = renderCapacity()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
