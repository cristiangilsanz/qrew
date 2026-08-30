// provides use resend phone otp
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { onboardingApi } from '../api'

// provides use resend phone otp
export function useResendPhoneOtp() {
  const { t } = useTranslation()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: { phone_number: string }) => onboardingApi.resendPhoneOtp(data),
    // handles on success
    onSuccess: () => {
      toast.success(t('onboarding.phone.resendSuccess'))
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('common.error'))
      toast.error(message)
    },
  })
}
