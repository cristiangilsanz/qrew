import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { ReservationSummary } from './ReservationSummary'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

const ACTIVE_RESERVATION = {
  id: 'res-1',
  event_id: 'event-1',
  ticket_type_id: 'tt-1',
  quantity: 2,
  status: 'reserved' as const,
  expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
  created_at: new Date().toISOString(),
}

function renderSummary(
  reservation = ACTIVE_RESERVATION,
  handlers: { onCancel?: () => void; onPay?: () => void } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReservationSummary reservation={reservation} {...handlers} />
    </QueryClientProvider>,
  )
}

describe('ReservationSummary', () => {
  it('shows quantity and countdown for an active reservation', () => {
    renderSummary()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/remaining/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pay now/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('calls onPay when pay button clicked', async () => {
    const onPay = vi.fn()
    renderSummary(ACTIVE_RESERVATION, { onPay })
    await userEvent.click(screen.getByRole('button', { name: /pay now/i }))
    expect(onPay).toHaveBeenCalled()
  })

  it('shows cancelled state when reservation is cancelled', () => {
    renderSummary({ ...ACTIVE_RESERVATION, status: 'cancelled' })
    expect(screen.getByText(/this reservation was cancelled/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /pay now/i })).not.toBeInTheDocument()
  })

  it('shows paid state when reservation is paid', () => {
    renderSummary({ ...ACTIVE_RESERVATION, status: 'paid' })
    expect(screen.getByText(/payment confirmed/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /pay now/i })).not.toBeInTheDocument()
  })

  it('cancels reservation and calls onCancel callback', async () => {
    const { toast } = await import('sonner')
    const onCancel = vi.fn()
    server.use(
      http.post('http://localhost:8003/v1/reservations/:id/cancel', () =>
        HttpResponse.json({ ...ACTIVE_RESERVATION, status: 'cancelled' }),
      ),
    )
    renderSummary(ACTIVE_RESERVATION, { onCancel })
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled()
      expect(onCancel).toHaveBeenCalled()
    })
  })
})
