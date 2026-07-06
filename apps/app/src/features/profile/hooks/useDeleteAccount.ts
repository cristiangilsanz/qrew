import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

export function useDeleteAccount() {
  const { t } = useTranslation()
  const clearSession = useAuthStore((s) => s.clearSession)
  return useMutation({
    mutationFn: (current_password: string) => profileApi.deleteAccount(current_password),
    onSuccess: () => {
      toast.success(t('profile.deleteAccount.success'))
      clearSession()
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('profile.errors.deleteAccountFailed'),
      )
      toast.error(message)
    },
  })
}
