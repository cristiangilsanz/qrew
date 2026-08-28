// provides use change phone
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { profileApi } from '../api'

// provides use change phone
export function useChangePhone(onSuccess?: () => void) {
  const { t } = useTranslation()
  return useMutation({
    // implements mutation fn
    mutationFn: (data: { new_phone_number: string; current_password: string }) =>
      profileApi.changePhone(data),
    // handles on success
    onSuccess: () => {
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('profile.errors.changePhoneFailed'),
      )
      toast.error(message)
    },
  })
}
