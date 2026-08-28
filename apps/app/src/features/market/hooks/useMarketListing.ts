// provides use market listing
import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

// provides use market listing
export function useMarketListing(ticketId: string, enabled = true) {
  return useQuery({
    queryKey: ['market', 'listing', ticketId],
    // implements query fn
    queryFn: () => marketApi.getListing(ticketId),
    enabled: !!ticketId && enabled,
    retry: false,
  })
}
