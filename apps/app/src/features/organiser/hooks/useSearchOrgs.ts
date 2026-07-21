import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

export function useSearchOrgs(q: string) {
  return useQuery({
    queryKey: ['organisations', 'search', q],
    queryFn: () => organiserApi.searchOrgs(q),
    enabled: q.trim().length > 0,
  })
}
