import { paymentsClient } from '@/lib/paymentsApi'
import { salesClient } from '@/lib/salesApi'

export type MarketQueueState = 'in_queue' | 'not_in_queue'
export type MarketListingState = 'available' | 'assigned' | 'completed' | 'cancelled'
export type MarketAssignmentState = 'pending' | 'paid' | 'expired' | 'declined'

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

export interface MarketAssignmentResponse {
  id: string
  listing_id: string
  event_id: string
  ticket_type_id: string | null
  assigned_at: string
  expires_at: string
  paid_at: string | null
  state: MarketAssignmentState
  holder_name: string | null
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

export interface MarketAssignmentPayment {
  id: string
  reservation_id: string
  amount_cents: number
  currency: string
  status: string
  client_secret: string
  created_at: string
}

export const marketApi = {
  // Queue
  joinQueue: (eventId: string) =>
    salesClient.post(`/v1/events/${eventId}/market/queue/join`).then((r) => r.data),

  leaveQueue: (eventId: string) =>
    salesClient.delete(`/v1/events/${eventId}/market/queue/leave`).then((r) => r.data),

  getQueueStatus: (eventId: string) =>
    salesClient
      .get<MarketQueueStatus>(`/v1/events/${eventId}/market/queue/status`)
      .then((r) => r.data),

  // Listings
  listTicket: (ticketId: string) =>
    salesClient
      .post<MarketListingResponse>(`/v1/tickets/${ticketId}/market/list`)
      .then((r) => r.data),

  getListing: (ticketId: string) =>
    salesClient
      .get<MarketListingResponse>(`/v1/tickets/${ticketId}/market/listing`)
      .then((r) => r.data),

  // My queues
  getMyQueues: () => salesClient.get<MarketQueueEntry[]>('/v1/market/queues').then((r) => r.data),

  // Assignments
  getPendingAssignment: () =>
    salesClient
      .get<MarketAssignmentResponse | null>('/v1/market/assignments/pending')
      .then((r) => r.data),

  getAssignment: (assignmentId: string) =>
    salesClient
      .get<MarketAssignmentResponse>(`/v1/market/assignments/${assignmentId}`)
      .then((r) => r.data),

  setHolders: (assignmentId: string, holder_name: string, holder_dni: string) =>
    salesClient
      .put<MarketAssignmentResponse>(`/v1/market/assignments/${assignmentId}/holders`, {
        holder_name,
        holder_dni,
      })
      .then((r) => r.data),

  declineAssignment: (assignmentId: string) =>
    salesClient.post(`/v1/market/assignments/${assignmentId}/decline`).then((r) => r.data),

  // Payments
  initiateAssignmentPayment: (assignmentId: string) =>
    paymentsClient
      .post<MarketAssignmentPayment>(`/v1/market-assignments/${assignmentId}/payment`)
      .then((r) => r.data),
}
