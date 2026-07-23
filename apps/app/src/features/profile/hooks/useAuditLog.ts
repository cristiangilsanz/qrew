import { useQuery } from '@tanstack/react-query'

import { profileApi } from '../api'

export function useAuditLog() {
  return useQuery({
    queryKey: ['audit-log'],
    queryFn: () => profileApi.getAuditLog(),
  })
}
