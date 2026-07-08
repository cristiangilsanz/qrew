import { paymentsClient } from '@/lib/paymentsApi'
import { salesClient } from '@/lib/salesApi'

export interface QueueJoinResponse {
  position: number
}

export interface QueuePositionResponse {
  position: number | null
}

export interface QueueRedeemResponse {
  reservation_window_token: string
}

export type ReservationStatus = 'reserved' | 'paid' | 'cancelled' | 'expired'

export interface Reservation {
  id: string
  event_id: string
  ticket_type_id: string
  quantity: number
  status: ReservationStatus
  expires_at: string
  created_at: string
}

export type PaymentStatus = 'requires_action' | 'processing' | 'succeeded' | 'failed' | 'refunded'

export interface Payment {
  id: string
  reservation_id: string
  amount_cents: number
  currency: string
  status: PaymentStatus
  client_secret: string
  created_at: string
}

export const ticketsApi = {
  joinQueue: (eventId: string) =>
    salesClient.post<QueueJoinResponse>(`/v1/events/${eventId}/queue/join`).then((r) => r.data),

  getQueuePosition: (eventId: string) =>
    salesClient
      .get<QueuePositionResponse>(`/v1/events/${eventId}/queue/position`)
      .then((r) => r.data),

  redeemQueue: (eventId: string, redeemWindowToken: string) =>
    salesClient
      .post<QueueRedeemResponse>(`/v1/events/${eventId}/queue/redeem`, {
        redeem_window_token: redeemWindowToken,
      })
      .then((r) => r.data),

  createReservation: (
    eventId: string,
    data: { ticket_type_id: string; quantity: number; reservation_window_token?: string },
  ) => salesClient.post<Reservation>(`/v1/events/${eventId}/reserve`, data).then((r) => r.data),

  getReservation: (reservationId: string) =>
    salesClient.get<Reservation>(`/v1/reservations/${reservationId}`).then((r) => r.data),

  cancelReservation: (reservationId: string) =>
    salesClient.post<Reservation>(`/v1/reservations/${reservationId}/cancel`).then((r) => r.data),

  initiatePayment: (reservationId: string) =>
    paymentsClient.post<Payment>(`/v1/reservations/${reservationId}/payment`).then((r) => r.data),
}
