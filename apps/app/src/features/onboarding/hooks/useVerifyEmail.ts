// provides use verify email
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { onboardingApi } from '../api'

// provides use verify email
export function useVerifyEmail(onSuccess?: () => void) {
  const { t } = useTranslation()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: { token: string }) => onboardingApi.verifyEmail(data),
    // handles on success
    onSuccess: () => {
      toast.success(t('onboarding.email.successToast'))
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('onboarding.errors.verifyEmailFailed'),
      )
      toast.error(message)
    },
  })
}
