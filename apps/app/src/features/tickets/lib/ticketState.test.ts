// tests the state a ticket shows while its reservation window runs out
import { describe, expect, it } from 'vitest'

import type { Reservation, Ticket } from '../api'
import { displayTicketState } from './ticketState'

// builds a ticket in the state under test
function ticket(state: Ticket['state']): Ticket {
  return {
    id: 'ticket-1',
    reservation_id: 'res-1',
    event_id: 'event-1',
    ticket_type_id: 'tier-1',
    state,
    state_updated_at: null,
    issued_at: null,
    expired_at: null,
    holder_name: null,
    holder_document_type: null,
    holder_dni: null,
    created_at: '2026-01-01T00:00:00Z',
    qr_eligible: false,
    counts_toward_limit: true,
  }
}

// builds the reservation the ticket belongs to
function reservation(status: Reservation['status'], expiresAt: string): Reservation {
  return {
    id: 'res-1',
    event_id: 'event-1',
    items: [],
    quantity: 1,
    status,
    expires_at: expiresAt,
    created_at: '2026-01-01T00:00:00Z',
  }
}

const FUTURE = new Date(Date.now() + 60_000).toISOString()
const PAST = new Date(Date.now() - 60_000).toISOString()

describe('displayTicketState', () => {
  // verifies that a reserved ticket reads as expired once its window closed
  it('reports a reserved ticket as expired when its window has passed', () => {
    expect(displayTicketState(ticket('reserved'), reservation('reserved', PAST))).toBe('expired')
  })

  // verifies that an expired reservation expires its ticket whatever the clock says
  it('reports a reserved ticket as expired when the reservation says so', () => {
    expect(displayTicketState(ticket('reserved'), reservation('expired', FUTURE))).toBe('expired')
  })

  // verifies that a live window leaves the ticket alone
  it('leaves a reserved ticket alone while its window is open', () => {
    expect(displayTicketState(ticket('reserved'), reservation('reserved', FUTURE))).toBe('reserved')
  })

  // verifies that any other state is reported as stored
  it('never rewrites a state other than reserved', () => {
    expect(displayTicketState(ticket('issued'), reservation('expired', PAST))).toBe('issued')
    expect(displayTicketState(ticket('redeemed'))).toBe('redeemed')
  })
})
