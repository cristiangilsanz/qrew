// provides use profile
import { useQuery } from '@tanstack/react-query'

import { profileApi } from '../api'

// provides use profile
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getMe,
  })
}
