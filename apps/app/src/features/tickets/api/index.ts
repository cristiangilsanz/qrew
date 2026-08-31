// implements tickets api
import type { DocumentType } from '@/lib/documents'
import { paymentsClient } from '@/lib/paymentsApi'
import { salesClient } from '@/lib/salesApi'
import { ticketingClient } from '@/lib/ticketingApi'

export interface QueueJoinResponse {
  position: number
}

export interface QueuePositionResponse {
  position: number | null
  redeem_token: string | null
}

export interface QueueRedeemResponse {
  reservation_window_token: string
}

export type ReservationStatus = 'reserved' | 'paid' | 'cancelled' | 'expired'

export interface ReservationItem {
  ticket_type_id: string
  quantity: number
}

export interface Reservation {
  id: string
  event_id: string
  items: ReservationItem[]
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

export type TicketState =
  'reserved' | 'issued' | 'scanning' | 'redeemed' | 'cancelled' | 'expired' | 'on_sale' | 'flagged'

export interface Ticket {
  id: string
  reservation_id: string
  event_id: string
  ticket_type_id: string
  state: TicketState
  state_updated_at: string | null
  issued_at: string | null
  expired_at: string | null
  holder_name: string | null
  holder_document_type: DocumentType | null
  holder_dni: string | null
  created_at: string
  qr_eligible: boolean
  counts_toward_limit: boolean
}

export interface HolderInput {
  position: number
  holder_name: string
  holder_document_type: DocumentType
  holder_dni: string
}

export interface QrToken {
  ticket_id: string
  jwt: string
  jti: string
  issued_at: string
  expires_at: string
  rotates_at: string
}

export const ticketsApi = {
  // implements join queue
  joinQueue: (eventId: string) =>
    salesClient.post<QueueJoinResponse>(`/v1/events/${eventId}/queue/join`).then((r) => r.data),

  // implements get queue position
  getQueuePosition: (eventId: string) =>
    salesClient
      .get<QueuePositionResponse>(`/v1/events/${eventId}/queue/position`)
      .then((r) => r.data),

  // implements redeem queue
  redeemQueue: (eventId: string, redeemWindowToken: string) =>
    salesClient
      .post<QueueRedeemResponse>(`/v1/events/${eventId}/queue/redeem`, {
        redeem_window_token: redeemWindowToken,
      })
      .then((r) => r.data),

  // implements create reservation
  createReservation: (
    eventId: string,
    data: { items: ReservationItem[]; reservation_window_token?: string },
  ) => salesClient.post<Reservation>(`/v1/events/${eventId}/reserve`, data).then((r) => r.data),

  // implements get reservation
  getReservation: (reservationId: string) =>
    salesClient.get<Reservation>(`/v1/reservations/${reservationId}`).then((r) => r.data),

  // implements cancel reservation
  cancelReservation: (reservationId: string) =>
    salesClient.post<Reservation>(`/v1/reservations/${reservationId}/cancel`).then((r) => r.data),

  // implements initiate payment
  initiatePayment: (reservationId: string) =>
    paymentsClient.post<Payment>(`/v1/reservations/${reservationId}/payment`).then((r) => r.data),

  // implements list tickets
  listTickets: () => ticketingClient.get<Ticket[]>('/v1/tickets').then((r) => r.data),

  // implements get ticket
  getTicket: (ticketId: string) =>
    ticketingClient.get<Ticket>(`/v1/tickets/${ticketId}`).then((r) => r.data),

  // implements get qr
  getQr: (ticketId: string, latitude: number, longitude: number) =>
    ticketingClient
      .get<QrToken>(`/v1/tickets/${ticketId}/qr`, { params: { latitude, longitude } })
      .then((r) => r.data),

  // implements set holders
  setHolders: (reservationId: string, holders: HolderInput[]) =>
    salesClient.put(`/v1/reservations/${reservationId}/holders`, { holders }).then((r) => r.data),
}
