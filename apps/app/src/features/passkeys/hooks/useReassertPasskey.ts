// provides use reassert passkey
import { Capacitor } from '@capacitor/core'
import { Passkeys } from '@capawesome/capacitor-passkeys'
import { startAuthentication } from '@simplewebauthn/browser'
import { useCallback } from 'react'

import { useAuthStore } from '@/store/auth'

import { reassertApi } from '../api/reassert'

// proves the holder is present and returns a token stamped with that moment,
// which is what the gate reads before it mints a code
export function useReassertPasskey() {
  return useCallback(async (): Promise<string> => {
    const options = await reassertApi.begin()
    const credential = Capacitor.isNativePlatform()
      ? await Passkeys.getPasskey({
          challenge: options.challenge,
          rpId: options.rpId,
          userVerification: options.userVerification,
        })
      : await startAuthentication({ optionsJSON: options as never })
    const result = await reassertApi.complete(credential)
    useAuthStore.getState().setAccessToken(result.access_token)
    return result.access_token
  }, [])
}
