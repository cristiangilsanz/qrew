// provides use sessions
import { useQuery } from '@tanstack/react-query'

import { profileApi } from '../api'

// provides use sessions
export function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: profileApi.getSessions,
  })
}
