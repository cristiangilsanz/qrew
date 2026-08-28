// provides use verify phone
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { onboardingApi } from '../api'

// provides use verify phone
export function useVerifyPhone(onSuccess?: () => void) {
  const { t } = useTranslation()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: { phone_number: string; otp: string }) => onboardingApi.verifyPhone(data),
    // handles on success
    onSuccess: () => {
      toast.success(t('onboarding.phone.successToast'))
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('onboarding.errors.verifyPhoneFailed'),
      )
      toast.error(message)
    },
  })
}
