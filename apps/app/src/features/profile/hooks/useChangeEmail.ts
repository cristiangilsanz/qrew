// provides use change email
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { profileApi } from '../api'

// provides use change email
export function useChangeEmail(onSuccess?: () => void) {
  const { t } = useTranslation()
  return useMutation({
    // implements mutation fn
    mutationFn: (data: { new_email: string; current_password: string }) =>
      profileApi.changeEmail(data),
    // handles on success
    onSuccess: () => {
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('profile.errors.changeEmailFailed'),
      )
      toast.error(message)
    },
  })
}
