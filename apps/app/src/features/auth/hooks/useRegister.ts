import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, authApi, extractErrorMessage, type RegisterRequest } from '../api'

export function useRegister() {
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('auth.errors.registerFailed'),
      )
      toast.error(message)
    },
  })
}
