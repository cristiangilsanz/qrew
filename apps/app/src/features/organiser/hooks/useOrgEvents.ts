// provides use org events
import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

// provides use org events
export function useOrgEvents(orgId: string) {
  return useQuery({
    queryKey: ['org-events', orgId],
    // implements query fn
    queryFn: () => organiserApi.listOrgEvents(orgId),
    enabled: !!orgId,
  })
}
