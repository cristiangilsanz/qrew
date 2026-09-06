// provides use revoke session
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { profileApi } from '../api'

// provides use revoke session
export function useRevokeSession() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    // implements mutation fn
    mutationFn: (jti: string) => profileApi.revokeSession(jti),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast.success(t('profile.sessions.revokeSuccess'))
    },
  })
}
