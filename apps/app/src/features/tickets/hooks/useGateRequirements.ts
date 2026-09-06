// provides use gate requirements
import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

// the switches rarely move, so one read per session is enough
const STALE_MS = 5 * 60 * 1000

// provides use gate requirements
export function useGateRequirements() {
  return useQuery({
    queryKey: ['gate-requirements'],
    // implements query fn
    queryFn: () => ticketsApi.gateRequirements(),
    staleTime: STALE_MS,
  })
}
