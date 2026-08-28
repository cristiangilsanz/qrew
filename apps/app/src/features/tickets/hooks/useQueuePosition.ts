// provides use queue position
import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

// provides use queue position
export function useQueuePosition(eventId: string, enabled = true) {
  return useQuery({
    queryKey: ['queue-position', eventId],
    // implements query fn
    queryFn: () => ticketsApi.getQueuePosition(eventId),
    enabled: !!eventId && enabled,
    refetchInterval: 2_000,
  })
}
