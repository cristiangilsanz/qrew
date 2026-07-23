import { http, HttpResponse } from 'msw'

const PAYMENTS_URL = 'http://localhost:8000/api/payments'

export const paymentsHandlers = [
  http.post(`${PAYMENTS_URL}/v1/reservations/:reservationId/payment`, () =>
    HttpResponse.json(
      {
        id: 'pay-1',
        reservation_id: 'res-1',
        amount_cents: 5000,
        currency: 'EUR',
        status: 'requires_action',
        client_secret: 'pi_test_secret_mock',
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    ),
  ),
]
