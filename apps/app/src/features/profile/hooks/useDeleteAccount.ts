// provides use delete account
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

// provides use delete account
export function useDeleteAccount(onDeleted?: () => void) {
  const { t } = useTranslation()
  // implements clear session
  const clearSession = useAuthStore((s) => s.clearSession)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  return useMutation({
    // implements mutation fn
    mutationFn: (current_password: string) => profileApi.deleteAccount(current_password),
    // clears the session and leaves for the login screen rather than waiting for the
    // route guard to notice on whatever the user happens to touch next
    onSuccess: () => {
      toast.success(t('profile.deleteAccount.success'))
      onDeleted?.()
      clearSession()
      queryClient.clear()
      void navigate({ to: '/login', replace: true })
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('profile.errors.deleteAccountFailed'))
      toast.error(message)
    },
  })
}
