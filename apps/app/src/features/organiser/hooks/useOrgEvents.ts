import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

export function useOrgEvents(orgId: string) {
  return useQuery({
    queryKey: ['org-events', orgId],
    queryFn: () => organiserApi.listOrgEvents(orgId),
    enabled: !!orgId,
  })
}
