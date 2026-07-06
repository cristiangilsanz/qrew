import { useQuery } from '@tanstack/react-query'

import { eventsApi } from '../api'

export function useEvent(id: string) {
  return useQuery({
    queryKey: ['events', id],
    queryFn: () => eventsApi.getById(id),
    enabled: !!id,
  })
}
