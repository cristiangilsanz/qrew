// provides use register
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { toastErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth'

import { type ApiErrorDetail, authApi, type RegisterRequest } from '../api'

// provides use register
export function useRegister() {
  const { t } = useTranslation()
  // implements set phone number
  const setPhoneNumber = useAuthStore((s) => s.setPhoneNumber)

  return useMutation({
    // implements mutation fn
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    // handles on success
    onSuccess: (_data, variables) => {
      setPhoneNumber(variables.phone_number)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('auth.errors.registerFailed'))
      toast.error(message)
    },
  })
}
