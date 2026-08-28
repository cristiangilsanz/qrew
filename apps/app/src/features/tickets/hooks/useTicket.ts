// provides use ticket
import { useQuery } from '@tanstack/react-query'

import { ticketsApi } from '../api'

// provides use ticket
export function useTicket(ticketId: string) {
  return useQuery({
    queryKey: ['ticket', ticketId],
    // implements query fn
    queryFn: () => ticketsApi.getTicket(ticketId),
    enabled: !!ticketId,
  })
}
