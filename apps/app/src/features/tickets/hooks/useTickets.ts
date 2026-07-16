import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

export function useTickets() {
  return useQuery({
    queryKey: ['tickets'],
    queryFn: () => ticketsApi.listTickets(),
  })
}
