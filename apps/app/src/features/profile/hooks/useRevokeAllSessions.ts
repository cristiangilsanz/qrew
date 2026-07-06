import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { profileApi } from '../api'

export function useRevokeAllSessions() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profileApi.revokeAllSessions,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast.success(t('profile.sessions.revokeAllSuccess'))
    },
  })
}
