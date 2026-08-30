// provides use market assignment
import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

// provides use market assignment
export function useMarketOffer(offerId: string) {
  return useQuery({
    queryKey: ['market', 'assignment', offerId],
    // implements query fn
    queryFn: () => marketApi.getOffer(offerId),
    enabled: !!offerId,
    // implements refetch interval
    refetchInterval: (query) => {
      const state = query.state.data?.state
      return state === 'pending' ? 15_000 : false
    },
  })
}

// provides use market assignments
export function useMarketOffers() {
  return useQuery({
    queryKey: ['market', 'assignments'],
    // implements query fn
    queryFn: () => marketApi.listOffers(),
    refetchInterval: 30_000,
  })
}

// provides use pending market assignment
export function usePendingMarketOffer() {
  return useQuery({
    queryKey: ['market', 'assignment', 'pending'],
    // implements query fn
    queryFn: () => marketApi.getPendingOffer(),
    refetchInterval: 30_000,
  })
}
