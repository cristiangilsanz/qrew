import { catalogClient } from '@/lib/catalogApi'

export interface EventSummary {
  id: string
  name: string
  description: string | null
  image_url: string | null
  organiser_name: string | null
  venue_city: string | null
  starts_at: string | null
  rank: number | null
}

export interface TicketType {
  id: string
  name: string
  description: string | null
  capacity: number
  reserved_count: number
  available: number
  price_cents: number
  currency: string
  position: number
}

export interface EventDetail {
  id: string
  name: string
  description: string | null
  image_url: string | null
  starts_at: string
  ends_at: string
  sale_starts_at: string
  sale_ends_at: string
  max_tickets_per_user: number
  queue_required: boolean
  published_at: string | null
  organisation: {
    id: string
    slug: string
    name: string
    description: string | null
  }
  venue: {
    id: string
    name: string
    city: string
    country: string
    latitude: number
    longitude: number
    geofence_radius_m: number
    timezone: string
  }
  ticket_types: TicketType[]
}

export interface EventFilters {
  q?: string
  city?: string
  cities?: string[]
  category?: string
  from?: string
  to?: string
  cursor?: string
  limit?: number
}

export const eventsApi = {
  list: (filters: EventFilters = {}) =>
    catalogClient
      .get<{ items: EventSummary[]; next_cursor: string | null }>('/v1/events', { params: filters })
      .then((r) => r.data),

  getById: (id: string) => catalogClient.get<EventDetail>(`/v1/events/${id}`).then((r) => r.data),
}
