import { http, HttpResponse } from 'msw'

const CATALOG_URL = 'http://localhost:8002'

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
