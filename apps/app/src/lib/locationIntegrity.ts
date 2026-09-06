// reads the handset's own verdict on whether the position it reports is simulated
import { Capacitor, registerPlugin } from '@capacitor/core'

// mock: the operating system flagged the fix, clean: it did not, unknown: no signal
type LocationIntegrityStatus = 'mock' | 'clean' | 'unknown'

interface LocationIntegrityPlugin {
  check(): Promise<{ status: LocationIntegrityStatus }>
}

const LocationIntegrity = registerPlugin<LocationIntegrityPlugin>('LocationIntegrity')

// answers null wherever the platform has no such flag, so the gate can degrade
// instead of treating a browser or an iphone as a spoofer
export async function readLocationIsMock(): Promise<boolean | null> {
  if (Capacitor.getPlatform() !== 'android') return null
  if (!Capacitor.isPluginAvailable('LocationIntegrity')) return null
  try {
    const { status } = await LocationIntegrity.check()
    if (status === 'mock') return true
    if (status === 'clean') return false
    return null
  } catch {
    return null
  }
}
