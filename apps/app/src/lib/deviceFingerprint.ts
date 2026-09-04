// derives the stable mark that tells one device apart from another
import { deviceKeysSupported, devicePublicKey } from './deviceKey'

// hashes the device's own public key, so the mark is stable across sessions and
// carries nothing about the machine beyond a key this application already holds
export async function deviceFingerprint(): Promise<string | null> {
  if (!deviceKeysSupported()) return null
  try {
    const spki = await devicePublicKey()
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(spki))
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
  } catch {
    return null
  }
}
