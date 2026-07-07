import { catalogClient } from '@/lib/catalogApi'

export interface Organisation {
  id: string
  slug: string
  name: string
  description: string | null
  created_at: string
}

export interface OrgMember {
  organisation_id: string
  user_id: string
  role: 'member' | 'manager' | 'owner'
  joined_at: string
}

export interface OrgEvent {
  id: string
  organisation_id: string
  venue_id: string
  name: string
  description: string | null
  starts_at: string
  ends_at: string
  sale_starts_at: string
  sale_ends_at: string
  max_tickets_per_user: number
  status: 'draft' | 'published' | 'cancelled'
  organiser_name: string
  venue_city: string
  queue_required: boolean
  created_at: string
  published_at: string | null
  cancelled_at: string | null
}

export interface OrgTicketType {
  id: string
  event_id: string
  name: string
  description: string | null
  capacity: number
  reserved_count: number
  available: number
  price_cents: number
  currency: string
  position: number
  created_at: string
}

export interface Venue {
  id: string
  name: string
  city: string
  country: string
  latitude: number
  longitude: number
  geofence_radius_m: number
  timezone: string
}

export interface CreateEventData {
  venue_id: string
  name: string
  description?: string
  starts_at: string
  ends_at: string
  sale_starts_at: string
  sale_ends_at: string
  max_tickets_per_user?: number
}

export interface UpdateEventData {
  name?: string
  description?: string
  starts_at?: string
  ends_at?: string
  sale_starts_at?: string
  sale_ends_at?: string
  max_tickets_per_user?: number
}

export interface CreateTicketTypeData {
  name: string
  description?: string
  capacity: number
  price_cents: number
  currency: string
  position?: number
}

export interface UpdateTicketTypeData {
  name?: string
  description?: string
  capacity?: number
  price_cents?: number
  position?: number
}

export interface CreateVenueData {
  name: string
  address_line: string
  city: string
  country: string
  latitude: number
  longitude: number
  geofence_radius_m?: number
  timezone: string
  description?: string
}

export const organiserApi = {
  listMyOrgs: () =>
    catalogClient
      .get<{ items: Organisation[]; next_cursor: string | null }>('/v1/organisations')
      .then((r) => r.data),

  createOrg: (data: { slug: string; name: string; description?: string }) =>
    catalogClient.post<Organisation>('/v1/organisations', data).then((r) => r.data),

  inviteMember: (orgId: string, data: { email: string; role: 'member' | 'manager' | 'owner' }) =>
    catalogClient.post<OrgMember>(`/v1/organisations/${orgId}/members`, data).then((r) => r.data),

  removeMember: (orgId: string, userId: string) =>
    catalogClient.delete(`/v1/organisations/${orgId}/members/${userId}`),

  listOrgEvents: (orgId: string) =>
    catalogClient
      .get<{ items: OrgEvent[]; next_cursor: string | null }>(`/v1/organisations/${orgId}/events`)
      .then((r) => r.data),

  createEvent: (orgId: string, data: CreateEventData) =>
    catalogClient.post<OrgEvent>(`/v1/organisations/${orgId}/events`, data).then((r) => r.data),

  updateEvent: (eventId: string, data: UpdateEventData) =>
    catalogClient.patch<OrgEvent>(`/v1/events/${eventId}`, data).then((r) => r.data),

  publishEvent: (eventId: string) =>
    catalogClient.post<OrgEvent>(`/v1/events/${eventId}/publish`).then((r) => r.data),

  cancelEvent: (eventId: string) =>
    catalogClient.post<OrgEvent>(`/v1/events/${eventId}/cancel`).then((r) => r.data),

  listTicketTypes: (eventId: string) =>
    catalogClient
      .get<{ items: OrgTicketType[]; next_cursor: string | null }>(
        `/v1/events/${eventId}/ticket-types`,
      )
      .then((r) => r.data),

  createTicketType: (eventId: string, data: CreateTicketTypeData) =>
    catalogClient
      .post<OrgTicketType>(`/v1/events/${eventId}/ticket-types`, data)
      .then((r) => r.data),

  updateTicketType: (eventId: string, ttId: string, data: UpdateTicketTypeData) =>
    catalogClient
      .patch<OrgTicketType>(`/v1/events/${eventId}/ticket-types/${ttId}`, data)
      .then((r) => r.data),

  deleteTicketType: (eventId: string, ttId: string) =>
    catalogClient.delete(`/v1/events/${eventId}/ticket-types/${ttId}`),

  listVenues: () =>
    catalogClient
      .get<{ items: Venue[]; next_cursor: string | null }>('/v1/venues')
      .then((r) => r.data),

  createVenue: (data: CreateVenueData) =>
    catalogClient.post<Venue>('/v1/venues', data).then((r) => r.data),
}
