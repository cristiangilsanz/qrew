// derives the state a ticket should show while its row waits to be expired
import type { Reservation, Ticket, TicketState } from '../api'

// reports a reserved ticket as expired once its reservation window has closed
export function displayTicketState(ticket: Ticket, reservation?: Reservation): TicketState {
  if (ticket.state !== 'reserved' || !reservation) return ticket.state
  const windowClosed =
    reservation.status === 'expired' || new Date(reservation.expires_at) < new Date()
  return windowClosed ? 'expired' : ticket.state
}
