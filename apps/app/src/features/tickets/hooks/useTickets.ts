// provides use tickets
import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

// provides use tickets
export function useTickets() {
  return useQuery({
    queryKey: ['tickets'],
    // implements query fn
    queryFn: () => ticketsApi.listTickets(),
  })
}
