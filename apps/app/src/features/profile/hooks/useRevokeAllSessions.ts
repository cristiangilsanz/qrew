// provides use revoke all sessions
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { authApi } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

// provides use revoke all sessions
export function useRevokeAllSessions() {
  const { t } = useTranslation()
  // implements clear session
  const clearSession = useAuthStore((s) => s.clearSession)
  // implements refresh token
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: profileApi.revokeAllSessions,
    // handles on success
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
