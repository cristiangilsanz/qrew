// provides use audit log
import { useQuery } from '@tanstack/react-query'

import { profileApi } from '../api'

// provides use audit log
export function useAuditLog() {
  return useQuery({
    queryKey: ['audit-log'],
    // implements query fn
    queryFn: () => profileApi.getAuditLog(),
  })
}
