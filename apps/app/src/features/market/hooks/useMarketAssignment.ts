// provides use market assignment
import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

// provides use market assignment
export function useMarketAssignment(assignmentId: string) {
  return useQuery({
    queryKey: ['market', 'assignment', assignmentId],
    // implements query fn
    queryFn: () => marketApi.getAssignment(assignmentId),
    enabled: !!assignmentId,
    // implements refetch interval
    refetchInterval: (query) => {
      const state = query.state.data?.state
      return state === 'pending' ? 15_000 : false
    },
  })
}

// provides use pending market assignment
export function usePendingMarketAssignment() {
  return useQuery({
    queryKey: ['market', 'assignment', 'pending'],
    // implements query fn
    queryFn: () => marketApi.getPendingAssignment(),
    refetchInterval: 30_000,
  })
}
