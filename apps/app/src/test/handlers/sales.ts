import { http, HttpResponse } from 'msw'

const SALES_URL = 'http://localhost:8000/api/sales'

const RESERVATION = {
  id: 'res-1',
  event_id: 'event-1',
  ticket_type_id: 'tt-1',
  quantity: 2,
  status: 'reserved',
  expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
  created_at: new Date().toISOString(),
}

export const salesHandlers = [
  http.post(`${SALES_URL}/v1/events/:eventId/queue/join`, () => HttpResponse.json({ position: 5 })),

  http.get(`${SALES_URL}/v1/events/:eventId/queue/position`, () =>
    HttpResponse.json({ position: 3 }),
  ),

  http.post(`${SALES_URL}/v1/events/:eventId/queue/redeem`, () =>
    HttpResponse.json({ reservation_window_token: 'mock-window-token' }),
  ),

  http.post(`${SALES_URL}/v1/events/:eventId/reserve`, () =>
    HttpResponse.json(RESERVATION, { status: 201 }),
  ),

  http.get(`${SALES_URL}/v1/reservations/:reservationId`, () => HttpResponse.json(RESERVATION)),

  http.post(`${SALES_URL}/v1/reservations/:reservationId/cancel`, () =>
    HttpResponse.json({ ...RESERVATION, status: 'cancelled' }),
  ),
]
