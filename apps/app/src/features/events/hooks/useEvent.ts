// provides use event
import { useQuery } from '@tanstack/react-query'

import { eventsApi } from '../api'

// provides use event
export function useEvent(id: string) {
  return useQuery({
    queryKey: ['events', id],
    // implements query fn
    queryFn: () => eventsApi.getById(id),
    enabled: !!id,
  })
}
