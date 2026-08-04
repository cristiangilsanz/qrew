import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

export function useMarketQueueStatus(eventId: string, enabled = true) {
  return useQuery({
    queryKey: ['market', 'queue', eventId],
    queryFn: () => marketApi.getQueueStatus(eventId),
    enabled: !!eventId && enabled,
  })
}
