import { http, HttpResponse } from 'msw'

const CATALOG_URL = 'http://localhost:8000/api/catalog'

export const catalogHandlers = [
  http.get(`${CATALOG_URL}/v1/events`, () =>
    HttpResponse.json({
      items: [
        {
          id: 'event-1',
          name: 'Summer Fest',
          organiser_name: 'Qrew Events',
          venue_city: 'Barcelona',
          starts_at: '2026-08-15T20:00:00Z',
          rank: null,
        },
        {
          id: 'event-2',
          name: 'Tech Conference',
          organiser_name: 'Dev Community',
          venue_city: 'Madrid',
          starts_at: '2026-09-01T09:00:00Z',
          rank: null,
        },
      ],
      next_cursor: null,
    }),
  ),

  http.get(`${CATALOG_URL}/v1/organisations`, () =>
    HttpResponse.json({
      items: [
        {
          id: 'org-1',
          slug: 'my-org',
          name: 'My Org',
          description: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
      next_cursor: null,
    }),
  ),

  http.post(`${CATALOG_URL}/v1/organisations`, () =>
    HttpResponse.json(
      {
        id: 'org-new',
        slug: 'new-org',
        name: 'New Org',
        description: null,
        created_at: '2026-07-07T00:00:00Z',
      },
      { status: 201 },
    ),
  ),

  http.post(`${CATALOG_URL}/v1/organisations/:orgId/members`, () =>
    HttpResponse.json(
      {
        organisation_id: 'org-1',
        user_id: 'user-2',
        role: 'member',
        joined_at: '2026-07-07T00:00:00Z',
      },
      { status: 201 },
    ),
  ),

  http.delete(
    `${CATALOG_URL}/v1/organisations/:orgId/members/:userId`,
    () => new HttpResponse(null, { status: 204 }),
  ),

  http.get(`${CATALOG_URL}/v1/organisations/:orgId/events`, () =>
    HttpResponse.json({
      items: [
        {
          id: 'event-1',
          organisation_id: 'org-1',
          venue_id: 'venue-1',
          name: 'Summer Fest',
          description: null,
          starts_at: '2026-08-15T20:00:00Z',
          ends_at: '2026-08-15T23:59:00Z',
          sale_starts_at: '2026-07-01T00:00:00Z',
          sale_ends_at: '2026-08-14T23:59:00Z',
          max_tickets_per_user: 4,
          status: 'draft',
          organiser_name: 'My Org',
          venue_city: 'Barcelona',
          queue_required: false,
          created_at: '2026-07-01T00:00:00Z',
          published_at: null,
          cancelled_at: null,
        },
      ],
      next_cursor: null,
    }),
  ),

  http.post(`${CATALOG_URL}/v1/organisations/:orgId/events`, () =>
    HttpResponse.json(
      {
        id: 'event-new',
        organisation_id: 'org-1',
        venue_id: 'venue-1',
        name: 'New Event',
        description: null,
        starts_at: '2026-09-01T20:00:00Z',
        ends_at: '2026-09-01T23:00:00Z',
        sale_starts_at: '2026-08-01T00:00:00Z',
        sale_ends_at: '2026-08-31T23:59:00Z',
        max_tickets_per_user: 4,
        status: 'draft',
        organiser_name: 'My Org',
        venue_city: 'Barcelona',
        queue_required: false,
        created_at: '2026-07-07T00:00:00Z',
        published_at: null,
        cancelled_at: null,
      },
      { status: 201 },
    ),
  ),

  http.patch(`${CATALOG_URL}/v1/events/:eventId`, () =>
    HttpResponse.json({
      id: 'event-1',
      organisation_id: 'org-1',
      venue_id: 'venue-1',
      name: 'Updated Event',
      description: null,
      starts_at: '2026-08-15T20:00:00Z',
      ends_at: '2026-08-15T23:59:00Z',
      sale_starts_at: '2026-07-01T00:00:00Z',
      sale_ends_at: '2026-08-14T23:59:00Z',
      max_tickets_per_user: 4,
      status: 'draft',
      organiser_name: 'My Org',
      venue_city: 'Barcelona',
      queue_required: false,
      created_at: '2026-07-01T00:00:00Z',
      published_at: null,
      cancelled_at: null,
    }),
  ),

  http.post(`${CATALOG_URL}/v1/events/:eventId/publish`, () =>
    HttpResponse.json({
      id: 'event-1',
      status: 'published',
      published_at: '2026-07-07T00:00:00Z',
      organisation_id: 'org-1',
      venue_id: 'venue-1',
      name: 'Summer Fest',
      description: null,
      starts_at: '2026-08-15T20:00:00Z',
      ends_at: '2026-08-15T23:59:00Z',
      sale_starts_at: '2026-07-01T00:00:00Z',
      sale_ends_at: '2026-08-14T23:59:00Z',
      max_tickets_per_user: 4,
      organiser_name: 'My Org',
      venue_city: 'Barcelona',
      queue_required: false,
      created_at: '2026-07-01T00:00:00Z',
      cancelled_at: null,
    }),
  ),

  http.post(`${CATALOG_URL}/v1/events/:eventId/cancel`, () =>
    HttpResponse.json({
      id: 'event-1',
      status: 'cancelled',
      cancelled_at: '2026-07-07T00:00:00Z',
      organisation_id: 'org-1',
      venue_id: 'venue-1',
      name: 'Summer Fest',
      description: null,
      starts_at: '2026-08-15T20:00:00Z',
      ends_at: '2026-08-15T23:59:00Z',
      sale_starts_at: '2026-07-01T00:00:00Z',
      sale_ends_at: '2026-08-14T23:59:00Z',
      max_tickets_per_user: 4,
      organiser_name: 'My Org',
      venue_city: 'Barcelona',
      queue_required: false,
      created_at: '2026-07-01T00:00:00Z',
      published_at: null,
    }),
  ),

  http.get(`${CATALOG_URL}/v1/events/:eventId/ticket-types`, () =>
    HttpResponse.json({
      items: [
        {
          id: 'tt-1',
          event_id: 'event-1',
          name: 'General',
          description: null,
          capacity: 100,
          reserved_count: 20,
          available: 80,
          price_cents: 1500,
          currency: 'EUR',
          position: 1,
          created_at: '2026-07-01T00:00:00Z',
        },
      ],
      next_cursor: null,
    }),
  ),

  http.post(`${CATALOG_URL}/v1/events/:eventId/ticket-types`, () =>
    HttpResponse.json(
      {
        id: 'tt-new',
        event_id: 'event-1',
        name: 'General',
        description: null,
        capacity: 100,
        reserved_count: 0,
        available: 100,
        price_cents: 1500,
        currency: 'EUR',
        position: 1,
        created_at: '2026-07-07T00:00:00Z',
      },
      { status: 201 },
    ),
  ),

  http.patch(`${CATALOG_URL}/v1/events/:eventId/ticket-types/:ttId`, () =>
    HttpResponse.json({
      id: 'tt-1',
      event_id: 'event-1',
      name: 'General Updated',
      description: null,
      capacity: 200,
      reserved_count: 0,
      available: 200,
      price_cents: 2000,
      currency: 'EUR',
      position: 1,
      created_at: '2026-07-07T00:00:00Z',
    }),
  ),

  http.delete(
    `${CATALOG_URL}/v1/events/:eventId/ticket-types/:ttId`,
    () => new HttpResponse(null, { status: 204 }),
  ),

  http.post(`${CATALOG_URL}/v1/venues`, () =>
    HttpResponse.json(
      {
        id: 'venue-new',
        name: 'New Venue',
        city: 'Madrid',
        country: 'ES',
        latitude: 40.416,
        longitude: -3.703,
        geofence_radius_m: 200,
        timezone: 'Europe/Madrid',
      },
      { status: 201 },
    ),
  ),

  http.get(`${CATALOG_URL}/v1/events/:eventId`, ({ params }) => {
    if (params.eventId === 'event-1') {
      return HttpResponse.json({
        id: 'event-1',
        name: 'Summer Fest',
        description: 'The biggest summer festival in Barcelona.',
        starts_at: '2026-08-15T20:00:00Z',
        ends_at: '2026-08-15T23:59:00Z',
        sale_starts_at: '2026-07-01T00:00:00Z',
        sale_ends_at: '2026-08-14T23:59:00Z',
        max_tickets_per_user: 4,
        queue_required: false,
        published_at: '2026-07-01T00:00:00Z',
        organisation: {
          id: 'org-1',
          slug: 'qrew-events',
          name: 'Qrew Events',
          description: null,
        },
        venue: {
          id: 'venue-1',
          name: 'Parc de la Ciutadella',
          city: 'Barcelona',
          country: 'ES',
          latitude: 41.386,
          longitude: 2.186,
          geofence_radius_m: 200,
          timezone: 'Europe/Madrid',
        },
        ticket_types: [
          {
            id: 'tt-1',
            name: 'General',
            description: null,
            capacity: 500,
            reserved_count: 120,
            available: 380,
            price_cents: 2500,
            currency: 'EUR',
            position: 1,
          },
          {
            id: 'tt-2',
            name: 'VIP',
            description: 'Front row access',
            capacity: 50,
            reserved_count: 50,
            available: 0,
            price_cents: 7500,
            currency: 'EUR',
            position: 2,
          },
        ],
      })
    }
    return new HttpResponse(null, { status: 404 })
  }),
]
