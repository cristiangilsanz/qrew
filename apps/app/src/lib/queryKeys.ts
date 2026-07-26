export const queryKeys = {
  events: {
    all: ['events'] as const,
    lists: () => [...queryKeys.events.all, 'list'] as const,
    list: (filters: object) => [...queryKeys.events.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.events.all, id] as const,
  },
  orgEvents: {
    list: (orgId: string) => ['org-events', orgId] as const,
  },
  ticketTypes: {
    list: (eventId: string) => ['ticket-types', eventId] as const,
  },
  tickets: {
    all: ['tickets'] as const,
  },
  market: {
    queue: (eventId: string) => ['market', 'queue', eventId] as const,
  },
  queuePosition: {
    detail: (eventId: string) => ['queue-position', eventId] as const,
  },
  orgs: {
    all: ['orgs'] as const,
    detail: (orgId: string) => ['orgs', orgId] as const,
    members: (orgId: string) => ['org-members', orgId] as const,
    venues: (orgId: string) => ['org-venues', orgId] as const,
  },
  profile: {
    all: ['profile'] as const,
  },
}
