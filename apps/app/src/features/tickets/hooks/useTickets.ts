// provides use tickets
import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

// provides use tickets
export function useTickets(poll = false) {
  return useQuery({
    queryKey: ['tickets'],
    // implements query fn
    queryFn: () => ticketsApi.listTickets(),
    refetchInterval: poll ? 1_500 : false,
  })
}
