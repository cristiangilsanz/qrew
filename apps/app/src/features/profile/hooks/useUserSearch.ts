// provides use user search
import { useQuery } from '@tanstack/react-query'

import { profileApi } from '@/features/profile/api'

// provides use user search
export function useUserSearch(q: string) {
  return useQuery({
    queryKey: ['user-search', q],
    // implements query fn
    queryFn: () => profileApi.searchUsers(q),
    enabled: q.trim().length >= 2,
    staleTime: 30_000,
  })
}
