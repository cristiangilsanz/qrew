// provides use market queue status
import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

// provides use market queue status
export function useMarketQueueStatus(eventId: string, enabled = true) {
  return useQuery({
    queryKey: ['market', 'queue', eventId],
    // implements query fn
    queryFn: () => marketApi.getQueueStatus(eventId),
    enabled: !!eventId && enabled,
  })
}
