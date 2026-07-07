import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

export function useOrgTicketTypes(eventId: string) {
  return useQuery({
    queryKey: ['ticket-types', eventId],
    queryFn: () => organiserApi.listTicketTypes(eventId),
    enabled: !!eventId,
  })
}
