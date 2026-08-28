// provides use search orgs
import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

// provides use search orgs
export function useSearchOrgs(q: string) {
  return useQuery({
    queryKey: ['organisations', 'search', q],
    // implements query fn
    queryFn: () => organiserApi.searchOrgs(q),
    enabled: q.trim().length > 0,
  })
}
