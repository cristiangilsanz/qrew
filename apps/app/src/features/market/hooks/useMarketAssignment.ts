import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

export function useMarketAssignment(assignmentId: string) {
  return useQuery({
    queryKey: ['market', 'assignment', assignmentId],
    queryFn: () => marketApi.getAssignment(assignmentId),
    enabled: !!assignmentId,
    refetchInterval: (query) => {
      const state = query.state.data?.state
      return state === 'pending' ? 15_000 : false
    },
  })
}

export function usePendingMarketAssignment() {
  return useQuery({
    queryKey: ['market', 'assignment', 'pending'],
    queryFn: () => marketApi.getPendingAssignment(),
    refetchInterval: 30_000,
  })
}
