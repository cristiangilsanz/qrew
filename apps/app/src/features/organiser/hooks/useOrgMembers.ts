import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

export function useOrgMembers(orgId: string) {
  return useQuery({
    queryKey: ['org-members', orgId],
    queryFn: () => organiserApi.listMembers(orgId),
  })
}
