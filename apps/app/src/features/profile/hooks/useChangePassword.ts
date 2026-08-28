// provides use change password
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { profileApi } from '../api'

// provides use change password
export function useChangePassword(onSuccess?: () => void) {
  const { t } = useTranslation()
  return useMutation({
    // implements mutation fn
    mutationFn: (data: { current_password: string; new_password: string }) =>
      profileApi.changePassword(data),
    // handles on success
    onSuccess: () => {
      toast.success(t('profile.changePassword.success'))
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('profile.errors.changePasswordFailed'),
      )
      toast.error(message)
    },
  })
}
