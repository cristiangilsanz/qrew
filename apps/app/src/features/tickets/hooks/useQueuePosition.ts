import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

export function useQueuePosition(eventId: string, enabled = true) {
  return useQuery({
    queryKey: ['queue-position', eventId],
    queryFn: () => ticketsApi.getQueuePosition(eventId),
    enabled: !!eventId && enabled,
    refetchInterval: 2_000,
  })
}
