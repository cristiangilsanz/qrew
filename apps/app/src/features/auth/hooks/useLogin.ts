import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { useAuthStore } from '@/store/auth'

import { type ApiErrorDetail, authApi, extractErrorMessage, type LoginRequest } from '../api'

export function useLogin() {
  const { t } = useTranslation()
  const setTokens = useAuthStore((s) => s.setTokens)
  const setSetupToken = useAuthStore((s) => s.setSetupToken)

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (data) => {
      if (data.setup_required) {
        setSetupToken(data.access_token)
      } else {
        setTokens(data.access_token, data.refresh_token ?? '')
      }
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('auth.errors.loginFailed'),
      )
      toast.error(message)
    },
  })
}
