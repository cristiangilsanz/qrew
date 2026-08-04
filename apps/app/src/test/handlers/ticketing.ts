import { http, HttpResponse } from 'msw'

const TICKETING_URL = 'http://localhost:8000/api/ticketing'

export const TICKET_1 = {
  id: 'ticket-1',
  reservation_id: 'res-1',
  event_id: 'event-1',
  ticket_type_id: 'tt-1',
  state: 'issued',
  state_updated_at: null,
  created_at: new Date().toISOString(),
}

export const TICKET_2 = {
  id: 'ticket-2',
  reservation_id: 'res-2',
  event_id: 'event-1',
  ticket_type_id: 'tt-1',
  state: 'used',
  state_updated_at: null,
  created_at: new Date(Date.now() - 86400_000).toISOString(),
}

export const ticketingHandlers = [
  http.get(`${TICKETING_URL}/v1/tickets`, () => HttpResponse.json([TICKET_1, TICKET_2])),

  http.get(`${TICKETING_URL}/v1/tickets/:ticketId`, ({ params }) => {
    const tickets = [TICKET_1, TICKET_2]
    const ticket = tickets.find((t) => t.id === params.ticketId)
    if (!ticket) return HttpResponse.json({ message: 'Ticket not found' }, { status: 404 })
    return HttpResponse.json(ticket)
  }),

  http.get(`${TICKETING_URL}/v1/tickets/:ticketId/qr`, () =>
    HttpResponse.json({
      ticket_id: 'ticket-1',
      jwt: 'mock.qr.jwt',
      jti: 'mock-jti',
      issued_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 20_000).toISOString(),
      rotates_at: new Date(Date.now() + 20_000).toISOString(),
    }),
  ),
]
