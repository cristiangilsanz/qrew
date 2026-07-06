import { useQuery } from '@tanstack/react-query'

import { profileApi } from '../api'

export function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: profileApi.getSessions,
  })
}
