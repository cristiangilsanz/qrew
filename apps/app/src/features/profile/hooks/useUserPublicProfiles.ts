import { useQuery } from '@tanstack/react-query'

import { profileApi } from '@/features/profile/api'

export function useUserPublicProfiles(userIds: string[]) {
  return useQuery({
    queryKey: ['user-public-profiles', userIds],
    queryFn: () => profileApi.getPublicProfiles(userIds),
    enabled: userIds.length > 0,
  })
}
