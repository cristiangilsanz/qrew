// provides use enrol device
import { useCallback } from 'react'

import { profileApi } from '@/features/profile/api'
import { deviceKeysSupported, devicePublicKey, signChallenge } from '@/lib/deviceKey'

// names this device after the platform the browser reports, which is what its owner recognises
function deviceName(): string {
  const agent = typeof navigator === 'undefined' ? '' : navigator.userAgent
  if (/android/i.test(agent)) return 'Android device'
  if (/iphone|ipad|ipod/i.test(agent)) return 'iOS device'
  return 'This browser'
}

// an account trusts one device and enrols it on its own, so signing in from a
// phone the account has not enrolled yet claims it. an account that already
// trusts another device is left alone, since replacing it belongs to recovery.
export function useEnrolDevice() {
  return useCallback(async () => {
    if (!deviceKeysSupported()) return
    try {
      const devices = await profileApi.getDevices()
      if (devices.items.length > 0) return
      const { challenge } = await profileApi.beginDeviceBind()
      const [public_key, signature] = await Promise.all([
        devicePublicKey(),
        signChallenge(challenge),
      ])
      await profileApi.completeDeviceBind({ name: deviceName(), public_key, signature })
    } catch {
      // the session stands even if the enrolment does not go through
    }
  }, [])
}
