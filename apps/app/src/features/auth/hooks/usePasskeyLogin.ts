// provides use passkey login
import { Capacitor } from '@capacitor/core'
import { Passkeys } from '@capawesome/capacitor-passkeys'
import { startAuthentication } from '@simplewebauthn/browser'
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { toastErrorMessage } from '@/lib/errors'
import { useAuthStore } from '@/store/auth'

import { type ApiErrorDetail, authApi } from '../api'
import { useEnrolDevice } from './useEnrolDevice'
import { useReportFingerprint } from './useReportFingerprint'

// provides use passkey login
export function usePasskeyLogin() {
  const { t } = useTranslation()
  // implements set tokens
  const setTokens = useAuthStore((s) => s.setTokens)
  // implements report fingerprint
  const reportFingerprint = useReportFingerprint()
  // implements enrol device
  const enrolDevice = useEnrolDevice()
  // implements set setup token
  const setSetupToken = useAuthStore((s) => s.setSetupToken)

  return useMutation({
    // implements mutation fn
    mutationFn: async (email: string) => {
      const options = await authApi.passkeyAuthBegin(email)
      const credential = Capacitor.isNativePlatform()
        ? await Passkeys.getPasskey({
            challenge: options.challenge,
            rpId: options.rpId,
            userVerification: options.userVerification,
          })
        : await startAuthentication({ optionsJSON: options })
      return authApi.passkeyAuthComplete(credential)
    },
    // handles on success
    onSuccess: (data) => {
      if (data.setup_required) {
        setSetupToken(data.access_token)
      } else {
        setTokens(data.access_token, data.refresh_token ?? '')
        void reportFingerprint()
        void enrolDevice()
      }
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('passkeys.errors.loginFailed'))
      toast.error(message)
    },
  })
}
