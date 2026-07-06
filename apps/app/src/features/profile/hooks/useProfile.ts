import { useQuery } from '@tanstack/react-query'

import { profileApi } from '../api'

export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getMe,
  })
}
