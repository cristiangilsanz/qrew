import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { profileApi } from '../api'

export function useChangePassword(onSuccess?: () => void) {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      profileApi.changePassword(data),
    onSuccess: () => {
      toast.success(t('profile.changePassword.success'))
      onSuccess?.()
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('profile.errors.changePasswordFailed'),
      )
      toast.error(message)
    },
  })
}
