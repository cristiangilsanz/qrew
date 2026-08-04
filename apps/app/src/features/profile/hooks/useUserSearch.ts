import { useQuery } from '@tanstack/react-query'

import { profileApi } from '@/features/profile/api'

export function useUserSearch(q: string) {
  return useQuery({
    queryKey: ['user-search', q],
    queryFn: () => profileApi.searchUsers(q),
    enabled: q.trim().length >= 2,
    staleTime: 30_000,
  })
}
