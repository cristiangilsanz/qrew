import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { type CompleteSetupResponse, onboardingApi } from '../api'

export function useCompleteSetup(onSuccess?: (data: CompleteSetupResponse) => void) {
  const { t } = useTranslation()
  const completeSetup = useAuthStore((s) => s.completeSetup)

  return useMutation({
    mutationFn: () => onboardingApi.completeSetup(),
    onSuccess: (data) => {
      completeSetup(data.access_token)
      onSuccess?.(data)
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('onboarding.errors.completeFailed'),
      )
      toast.error(message)
    },
  })
}
