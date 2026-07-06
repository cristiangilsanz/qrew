import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { profileApi } from '../api'

export function useRevokeSession() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jti: string) => profileApi.revokeSession(jti),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast.success(t('profile.sessions.revokeSuccess'))
    },
  })
}
