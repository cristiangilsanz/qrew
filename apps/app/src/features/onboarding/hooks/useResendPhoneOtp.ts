import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { onboardingApi } from '../api'

export function useResendPhoneOtp() {
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: { phone_number: string }) => onboardingApi.resendPhoneOtp(data),
    onSuccess: () => {
      toast.success(t('onboarding.phone.resendSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(error.response?.data?.detail, t('common.error'))
      toast.error(message)
    },
  })
}
