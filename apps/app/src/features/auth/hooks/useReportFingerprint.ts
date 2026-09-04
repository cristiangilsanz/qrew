// provides use report fingerprint
import { useCallback } from 'react'

import { profileApi } from '@/features/profile/api'
import { deviceFingerprint } from '@/lib/deviceFingerprint'

// tells the server which device this session runs on, which is what feeds the
// signal that scores how many accounts share one machine. a failure here must
// never block a sign in, so it is swallowed.
export function useReportFingerprint() {
  return useCallback(async () => {
    try {
      const hash = await deviceFingerprint()
      if (hash) await profileApi.reportFingerprint(hash)
    } catch {
      // the session stands even if the mark never reaches the server
    }
  }, [])
}
