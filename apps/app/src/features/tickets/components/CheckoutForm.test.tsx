import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import type { TicketType } from '@/features/events/api'
import { server } from '@/test/server'

import { CheckoutForm } from './CheckoutForm'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

const TICKET_TYPES: TicketType[] = [
  {
    id: 'tt-1',
    name: 'General',
    description: null,
    capacity: 500,
    reserved_count: 120,
    available: 380,
    price_cents: 2500,
    currency: 'EUR',
    position: 1,
  },
  {
    id: 'tt-2',
    name: 'VIP',
    description: 'Front row access',
    capacity: 50,
    reserved_count: 50,
    available: 0,
    price_cents: 7500,
    currency: 'EUR',
    position: 2,
  },
]

function renderForm(onSuccess = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <CheckoutForm
        eventId="event-1"
        ticketTypes={TICKET_TYPES}
        maxPerUser={4}
        onSuccess={onSuccess}
      />
    </QueryClientProvider>,
  )
}

describe('CheckoutForm', () => {
  it('renders ticket type and quantity selectors', () => {
    renderForm()
    expect(screen.getByLabelText(/ticket type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reserve/i })).toBeInTheDocument()
  })

  it('shows sold out events ticket types as disabled in the selector', () => {
    renderForm()
    const options = screen.getAllByRole('option')
    const vipOption = options.find((o) => o.textContent?.includes('VIP'))
    expect(vipOption).toHaveAttribute('disabled')
  })

  it('calls onSuccess with the reservation after submit', async () => {
    const onSuccess = vi.fn()
    renderForm(onSuccess)
    await userEvent.click(screen.getByRole('button', { name: /reserve/i }))
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(expect.objectContaining({ id: 'res-1' }))
    })
  })

  it('shows error toast when reservation fails', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8003/v1/events/:eventId/reserve', () =>
        HttpResponse.json({ detail: 'No availability' }, { status: 409 }),
      ),
    )
    renderForm()
    await userEvent.click(screen.getByRole('button', { name: /reserve/i }))
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled()
    })
  })

  it('shows sold out message when all ticket types are unavailable', () => {
    const soldOutTypes = TICKET_TYPES.map((tt) => ({ ...tt, available: 0 }))
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <CheckoutForm
          eventId="event-1"
          ticketTypes={soldOutTypes}
          maxPerUser={4}
          onSuccess={vi.fn()}
        />
      </QueryClientProvider>,
    )
    expect(screen.getByText(/sold out/i)).toBeInTheDocument()
  })
})
