// provides use recover account
import { Capacitor } from '@capacitor/core'
import { Passkeys } from '@capawesome/capacitor-passkeys'
import { startRegistration } from '@simplewebauthn/browser'
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { recoveryApi } from '../api'

// walks the whole recovery in one go, since the token the first call returns is
// short lived and only serves to register the replacement key
export function useRecoverAccount(onSuccess: () => void) {
  const { t } = useTranslation()

  return useMutation({
    // implements mutation fn
    mutationFn: async (input: { email: string; file: File }) => {
      const started = await recoveryApi.begin(input)
      if (!started.recovery_token || !started.passkey_options) {
        throw new Error('recovery_rejected')
      }
      const options = JSON.parse(started.passkey_options) as Record<string, unknown>
      const credential = Capacitor.isNativePlatform()
        ? await Passkeys.createPasskey({
            challenge: options.challenge as string,
            rp: options.rp as never,
            user: options.user as never,
            pubKeyCredParams: options.pubKeyCredParams as never,
            authenticatorSelection: options.authenticatorSelection as never,
            timeout: options.timeout as number,
            attestation: options.attestation as never,
            excludeCredentials: options.excludeCredentials as never,
          })
        : await startRegistration({ optionsJSON: options as never })
      return recoveryApi.complete(started.recovery_token, credential)
    },
    // handles on success
    onSuccess: () => {
      toast.success(t('recovery.success'))
      onSuccess()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      toast.error(toastErrorMessage(error, t('recovery.errors.failed')))
    },
  })
}
