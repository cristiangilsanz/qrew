import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { profileApi } from '../api'

export function useConfirmPhoneChange(onSuccess?: () => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { new_phone_number: string; otp: string }) =>
      profileApi.confirmPhoneChange(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['profile'] })
      toast.success(t('profile.changePhone.success'))
      onSuccess?.()
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('profile.errors.confirmPhoneFailed'),
      )
      toast.error(message)
    },
  })
}
