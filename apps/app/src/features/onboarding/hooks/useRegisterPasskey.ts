import { startRegistration } from '@simplewebauthn/browser'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { onboardingApi } from '../api'

export function useRegisterPasskey(onSuccess?: () => void) {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: async () => {
      const options = await onboardingApi.passkeyRegisterBegin()
      const credential = await startRegistration({ optionsJSON: options })
      return onboardingApi.passkeyRegisterComplete(credential)
    },
    onSuccess: () => {
      toast.success(t('passkeys.registerSuccess'))
      onSuccess?.()
    },
    onError: () => {
      toast.error(t('passkeys.errors.registerFailed'))
    },
  })
}
