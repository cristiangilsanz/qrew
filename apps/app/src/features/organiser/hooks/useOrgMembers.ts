// provides use org members
import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

// provides use org members
export function useOrgMembers(orgId: string) {
  return useQuery({
    queryKey: ['org-members', orgId],
    // implements query fn
    queryFn: () => organiserApi.listMembers(orgId),
  })
}
