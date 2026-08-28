// implements query keys
export const queryKeys = {
  events: {
    all: ['events'] as const,
    // implements lists
    lists: () => [...queryKeys.events.all, 'list'] as const,
    // implements list
    list: (filters: object) => [...queryKeys.events.lists(), filters] as const,
    // implements detail
    detail: (id: string) => [...queryKeys.events.all, id] as const,
  },
  orgEvents: {
    // implements list
    list: (orgId: string) => ['org-events', orgId] as const,
  },
  ticketTypes: {
    // implements list
    list: (eventId: string) => ['ticket-types', eventId] as const,
  },
  tickets: {
    all: ['tickets'] as const,
  },
  market: {
    // implements queue
    queue: (eventId: string) => ['market', 'queue', eventId] as const,
  },
  queuePosition: {
    // implements detail
    detail: (eventId: string) => ['queue-position', eventId] as const,
  },
  orgs: {
    all: ['orgs'] as const,
    // implements detail
    detail: (orgId: string) => ['orgs', orgId] as const,
    // implements members
    members: (orgId: string) => ['org-members', orgId] as const,
    // implements venues
    venues: (orgId: string) => ['org-venues', orgId] as const,
  },
  profile: {
    all: ['profile'] as const,
  },
  entryStats: {
    // implements detail
    detail: (eventId: string) => ['entry-stats', eventId] as const,
  },
}
