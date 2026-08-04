import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

export function useMarketListing(ticketId: string, enabled = true) {
  return useQuery({
    queryKey: ['market', 'listing', ticketId],
    queryFn: () => marketApi.getListing(ticketId),
    enabled: !!ticketId && enabled,
    retry: false,
  })
}
