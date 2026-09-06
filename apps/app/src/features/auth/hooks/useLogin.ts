// provides use login
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { toastErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth'

import { type ApiErrorDetail, authApi, type LoginRequest } from '../api'
import { useEnrolDevice } from './useEnrolDevice'
import { useReportFingerprint } from './useReportFingerprint'

// provides use login
export function useLogin() {
  const { t } = useTranslation()
  // implements set tokens
  const setTokens = useAuthStore((s) => s.setTokens)
  // implements report fingerprint
  const reportFingerprint = useReportFingerprint()
  // implements enrol device
  const enrolDevice = useEnrolDevice()
  // implements set setup token
  const setSetupToken = useAuthStore((s) => s.setSetupToken)
  // implements set totp token
  const setTotpToken = useAuthStore((s) => s.setTotpToken)

  return useMutation({
    // implements mutation fn
    mutationFn: (data: LoginRequest) => authApi.login(data),
    // handles on success
    onSuccess: (data) => {
      if (data.setup_required) {
        setSetupToken(data.access_token)
      } else if (data.totp_required) {
        setTotpToken(data.access_token)
      } else {
        setTokens(data.access_token, data.refresh_token ?? '')
        void reportFingerprint()
        void enrolDevice()
      }
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('auth.errors.loginFailed'))
      toast.error(message)
    },
  })
}
