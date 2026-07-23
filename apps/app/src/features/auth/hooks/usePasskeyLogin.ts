import { startAuthentication } from '@simplewebauthn/browser'
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { useAuthStore } from '@/store/auth'

import { type ApiErrorDetail, authApi, extractErrorMessage } from '../api'

export function usePasskeyLogin() {
  const { t } = useTranslation()
  const setTokens = useAuthStore((s) => s.setTokens)
  const setSetupToken = useAuthStore((s) => s.setSetupToken)

  return useMutation({
    mutationFn: async (email: string) => {
      const options = await authApi.passkeyAuthBegin(email)
      const credential = await startAuthentication({ optionsJSON: options })
      return authApi.passkeyAuthComplete(credential)
    },
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
        t('passkeys.errors.loginFailed'),
      )
      toast.error(message)
    },
  })
}
