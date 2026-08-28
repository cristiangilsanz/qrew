// provides use user public profiles
import { useQuery } from '@tanstack/react-query'

import { profileApi } from '@/features/profile/api'

// provides use user public profiles
export function useUserPublicProfiles(userIds: string[]) {
  return useQuery({
    queryKey: ['user-public-profiles', userIds],
    // implements query fn
    queryFn: () => profileApi.getPublicProfiles(userIds),
    enabled: userIds.length > 0,
  })
}
