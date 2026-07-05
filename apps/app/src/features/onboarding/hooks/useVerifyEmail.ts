import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { onboardingApi } from '../api'

export function useVerifyEmail(onSuccess?: () => void) {
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: { token: string }) => onboardingApi.verifyEmail(data),
    onSuccess: () => {
      toast.success(t('onboarding.email.successToast'))
      onSuccess?.()
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('onboarding.errors.verifyEmailFailed'),
      )
      toast.error(message)
    },
  })
}
