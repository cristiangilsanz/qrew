import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

export function useTicket(ticketId: string) {
  return useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => ticketsApi.getTicket(ticketId),
    enabled: !!ticketId,
  })
}
