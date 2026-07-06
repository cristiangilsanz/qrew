import { useQuery } from '@tanstack/react-query'

import { type EventFilters, eventsApi } from '../api'

export function useEvents(filters: EventFilters = {}) {
  return useQuery({
    queryKey: ['events', filters],
    queryFn: () => eventsApi.list(filters),
  })
}
