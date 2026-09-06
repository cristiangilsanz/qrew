// provides use confirm phone change
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { profileApi } from '../api'

// provides use confirm phone change
export function useConfirmPhoneChange(onSuccess?: () => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    // implements mutation fn
    mutationFn: (data: { new_phone_number: string; otp: string }) =>
      profileApi.confirmPhoneChange(data),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['profile'] })
      toast.success(t('profile.changePhone.success'))
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('profile.errors.confirmPhoneFailed'))
      toast.error(message)
    },
  })
}
