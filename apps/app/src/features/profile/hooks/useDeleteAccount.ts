// provides use delete account
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

// provides use delete account
export function useDeleteAccount() {
  const { t } = useTranslation()
  // implements clear session
  const clearSession = useAuthStore((s) => s.clearSession)
  return useMutation({
    // implements mutation fn
    mutationFn: (current_password: string) => profileApi.deleteAccount(current_password),
    // handles on success
    onSuccess: () => {
      toast.success(t('profile.deleteAccount.success'))
      clearSession()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('profile.errors.deleteAccountFailed'))
      toast.error(message)
    },
  })
}
