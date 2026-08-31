// implements market api
import type { DocumentType } from '@/lib/documents'
import { paymentsClient } from '@/lib/paymentsApi'
import { salesClient } from '@/lib/salesApi'

export type MarketQueueState = 'in_queue' | 'not_in_queue'
export type MarketListingState = 'available' | 'assigned' | 'completed' | 'cancelled'
export type MarketOfferState = 'pending' | 'paid' | 'expired' | 'declined'

export interface MarketQueueStatus {
  in_queue: boolean
  joined_at: string | null
  queue_count: number
}

export interface MarketListingResponse {
  id: string
  ticket_id: string
  event_id: string
  ticket_type_id: string
  price_cents: number
  currency: string
  state: MarketListingState
  listed_at: string
  expires_at: string
  completed_at: string | null
  cancelled_at: string | null
}

export interface MarketOfferResponse {
  id: string
  listing_id: string
  event_id: string
  ticket_type_id: string | null
  assigned_at: string
  expires_at: string
  paid_at: string | null
  state: MarketOfferState
  holder_name: string | null
  holder_document_type: DocumentType | null
  holder_dni: string | null
  price_cents: number
  currency: string
  event_name: string | null
  ticket_type_name: string | null
}

export interface MarketQueueEntry {
  event_id: string
  joined_at: string
}

export interface MarketOfferPayment {
  id: string
  reservation_id: string
  amount_cents: number
  currency: string
  status: string
  client_secret: string
  created_at: string
}

export const marketApi = {
  // implements join queue
  joinQueue: (eventId: string) =>
    salesClient.post(`/v1/events/${eventId}/market/queue/join`).then((r) => r.data),

  // implements leave queue
  leaveQueue: (eventId: string) =>
    salesClient.delete(`/v1/events/${eventId}/market/queue/leave`).then((r) => r.data),

  // implements get queue status
  getQueueStatus: (eventId: string) =>
    salesClient
      .get<MarketQueueStatus>(`/v1/events/${eventId}/market/queue/status`)
      .then((r) => r.data),

  // implements list ticket
  listTicket: (ticketId: string) =>
    salesClient
      .post<MarketListingResponse>(`/v1/tickets/${ticketId}/market/list`)
      .then((r) => r.data),

  // implements get listing
  getListing: (ticketId: string) =>
    salesClient
      .get<MarketListingResponse>(`/v1/tickets/${ticketId}/market/listing`)
      .then((r) => r.data),

  // implements get my queues
  getMyQueues: () => salesClient.get<MarketQueueEntry[]>('/v1/market/queues').then((r) => r.data),

  // implements get pending assignment
  listOffers: () =>
    salesClient.get<MarketOfferResponse[]>('/v1/market/assignments').then((r) => r.data),

  getPendingOffer: () =>
    salesClient
      .get<MarketOfferResponse | null>('/v1/market/assignments/pending')
      .then((r) => r.data),

  // implements get assignment
  getOffer: (offerId: string) =>
    salesClient.get<MarketOfferResponse>(`/v1/market/assignments/${offerId}`).then((r) => r.data),

  // implements set holders
  setHolders: (
    offerId: string,
    holder_name: string,
    holder_dni: string,
    holder_document_type: DocumentType = 'dni',
  ) =>
    salesClient
      .put<MarketOfferResponse>(`/v1/market/assignments/${offerId}/holders`, {
        holder_name,
        holder_document_type,
        holder_dni,
      })
      .then((r) => r.data),

  // implements decline assignment
  declineOffer: (offerId: string) =>
    salesClient.post(`/v1/market/assignments/${offerId}/decline`).then((r) => r.data),

  // implements initiate assignment payment
  initiateOfferPayment: (offerId: string) =>
    paymentsClient
      .post<MarketOfferPayment>(`/v1/market-assignments/${offerId}/payment`)
      .then((r) => r.data),
}
