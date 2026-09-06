// provides use bind device
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { devicePublicKey, signChallenge } from '@/lib/deviceKey'
import { toastErrorMessage } from '@/lib/errors'

import { profileApi } from '../api'

// trusts this device by signing the challenge the server issues for it
export function useBindDevice() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // walks the two calls the binding takes, signing in between
    mutationFn: async (name: string) => {
      const { challenge } = await profileApi.beginDeviceBind()
      const [public_key, signature] = await Promise.all([
        devicePublicKey(),
        signChallenge(challenge),
      ])
      return profileApi.completeDeviceBind({ name, public_key, signature })
    },
    // handles on success
    onSuccess: () => {
      toast.success(t('profile.security.deviceTrusted'))
      void queryClient.invalidateQueries({ queryKey: ['devices'] })
    },
    // handles on error
    onError: (error) => {
      toast.error(toastErrorMessage(error, t('profile.security.deviceNotTrusted')))
    },
  })
}
