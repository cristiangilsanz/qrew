import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { authApi } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

export function useRevokeAllSessions() {
  const { t } = useTranslation()
  const clearSession = useAuthStore((s) => s.clearSession)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: profileApi.revokeAllSessions,
    onSuccess: () => {
      toast.success(t('profile.sessions.revokeAllSuccess'))
      if (refreshToken) {
        void authApi.logout(refreshToken).catch(() => {})
      }
      clearSession()
      void navigate({ to: '/login' })
    },
  })
}
