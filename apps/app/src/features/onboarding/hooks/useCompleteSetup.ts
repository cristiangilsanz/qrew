// provides use complete setup
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { type CompleteSetupResponse, onboardingApi } from '../api'

// provides use complete setup
export function useCompleteSetup(onSuccess?: (data: CompleteSetupResponse) => void) {
  const { t } = useTranslation()
  // implements complete setup
  const completeSetup = useAuthStore((s) => s.completeSetup)

  return useMutation({
    // implements mutation fn
    mutationFn: () => onboardingApi.completeSetup(),
    // handles on success
    onSuccess: (data) => {
      completeSetup(data.access_token)
      onSuccess?.(data)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('onboarding.errors.completeFailed'),
      )
      toast.error(message)
    },
  })
}
