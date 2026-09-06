// derives the state a ticket should show while its row waits for the pipeline to catch up
import type { Reservation, Ticket, TicketState } from '../api'

// the states a ticket can be shown in, including the ones no row ever stores
export type TicketDisplayState = TicketState | 'processing'

// reports a reserved ticket as expired once its window closed, or as processing once it is paid
export function displayTicketState(ticket: Ticket, reservation?: Reservation): TicketDisplayState {
  if (ticket.state !== 'reserved' || !reservation) return ticket.state
  // the payment landed but the events that issue the ticket have not been drained yet
  if (reservation.status === 'paid') return 'processing'
  const windowClosed =
    reservation.status === 'expired' || new Date(reservation.expires_at) < new Date()
  return windowClosed ? 'expired' : ticket.state
}
