// provides use org ticket types
import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

// provides use org ticket types
export function useOrgTicketTypes(eventId: string) {
  return useQuery({
    queryKey: ['ticket-types', eventId],
    // implements query fn
    queryFn: () => organiserApi.listTicketTypes(eventId),
    enabled: !!eventId,
  })
}
