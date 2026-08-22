import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { EventDetail } from '@/features/events/api'
import { server } from '@/test/server'

import type { Ticket } from '../api'
import { ReservationRow } from './ReservationRow'

const navigate = vi.fn()

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <span>{children}</span>,
  useNavigate: () => navigate,
}))

const SALES = 'http://localhost:8000/api/sales'

const EVENT = {
  id: 'event-1',
  name: 'Summer Fest',
  description: null,
  image_url: null,
  starts_at: '2026-08-15T20:00:00Z',
  ends_at: '2026-08-15T23:00:00Z',
  sale_starts_at: '2026-07-01T10:00:00Z',
  sale_ends_at: '2026-08-14T23:00:00Z',
  max_tickets_per_user: 4,
  queue_required: false,
  published_at: '2026-07-01T00:00:00Z',
  availability_status: 'on_sale',
  organisation: { id: 'org-1', slug: 'qrew', name: 'Qrew Events', description: null },
  venue: {
    id: 'venue-1',
    name: 'Palau Sant Jordi',
    city: 'Barcelona',
    country: 'ES',
    latitude: 41.36,
    longitude: 2.15,
    geofence_radius_m: 200,
    timezone: 'Europe/Madrid',
  },
  ticket_types: [],
} as unknown as EventDetail

function ticket(overrides: Partial<Ticket> = {}): Ticket {
  return {
    id: 'ticket-0000000001',
    reservation_id: 'res-1',
    event_id: 'event-1',
    ticket_type_id: 'tt-1',
    state: 'issued',
    state_updated_at: null,
    issued_at: '2026-07-02T10:00:00Z',
    expired_at: null,
    holder_name: null,
    holder_dni: null,
    created_at: '2026-07-02T10:00:00Z',
    qr_eligible: true,
    counts_toward_limit: true,
    ...overrides,
  }
}

function renderRow(tickets: Ticket[]) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReservationRow tickets={tickets} event={EVENT} />
    </QueryClientProvider>,
  )
}

describe('ReservationRow', () => {
  it('names the event, the organisation and the venue', () => {
    renderRow([ticket()])
    expect(screen.getByText('Summer Fest')).toBeInTheDocument()
    expect(screen.getByText('Qrew Events')).toBeInTheDocument()
    expect(screen.getByText(/palau sant jordi, barcelona/i)).toBeInTheDocument()
  })

  it('shows one stub per ticket and numbers them', () => {
    renderRow([ticket({ id: 'aaaaaaaa-1' }), ticket({ id: 'bbbbbbbb-2' })])
    expect(screen.getByText('#AAAAAAAA')).toBeInTheDocument()
    expect(screen.getByText('#BBBBBBBB')).toBeInTheDocument()
    expect(screen.getByText('1 of 2')).toBeInTheDocument()
  })

  it('keeps the payment call away from a ticket already issued', () => {
    renderRow([ticket()])
    expect(screen.queryByRole('button', { name: /complete payment/i })).not.toBeInTheDocument()
  })

  it('calls for payment while the reservation is still alive', async () => {
    server.use(
      http.get(`${SALES}/v1/reservations/:reservationId`, () =>
        HttpResponse.json({
          id: 'res-1',
          event_id: 'event-1',
          ticket_type_id: 'tt-1',
          quantity: 1,
          status: 'reserved',
          expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
          created_at: new Date().toISOString(),
        }),
      ),
    )
    renderRow([ticket({ state: 'reserved' })])
    const button = await screen.findByRole('button', { name: /complete payment/i })
    await userEvent.click(button)
    expect(navigate).toHaveBeenCalledWith({
      to: '/reservations/$reservationId',
      params: { reservationId: 'res-1' },
    })
  })

  it('marks the ticket as expired when its reservation ran out', async () => {
    server.use(
      http.get(`${SALES}/v1/reservations/:reservationId`, () =>
        HttpResponse.json({
          id: 'res-1',
          event_id: 'event-1',
          ticket_type_id: 'tt-1',
          quantity: 1,
          status: 'expired',
          expires_at: new Date(Date.now() - 60 * 1000).toISOString(),
          created_at: new Date().toISOString(),
        }),
      ),
    )
    renderRow([ticket({ state: 'reserved' })])
    await waitFor(() => {
      expect(screen.getByText(/expired/i)).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /complete payment/i })).not.toBeInTheDocument()
  })
})
