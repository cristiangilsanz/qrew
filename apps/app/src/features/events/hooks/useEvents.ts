// provides use events
import { useQuery } from '@tanstack/react-query'

import { type EventFilters, eventsApi } from '../api'

// provides use events
export function useEvents(filters: EventFilters = {}) {
  return useQuery({
    queryKey: ['events', filters],
    // implements query fn
    queryFn: () => eventsApi.list(filters),
  })
}
