// provides use kyc upload
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type KycUploadResponse, onboardingApi } from '../api'

// provides use kyc upload
export function useKycUpload(onSuccess?: (data: KycUploadResponse) => void) {
  const { t } = useTranslation()

  return useMutation({
    // implements mutation fn
    mutationFn: (file: File) => onboardingApi.uploadKyc(file),
    // handles on success
    onSuccess: (data) => {
      toast.success(t('onboarding.kyc.successToast'))
      onSuccess?.(data)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('onboarding.errors.kycUploadFailed'),
      )
      toast.error(message)
    },
  })
}
