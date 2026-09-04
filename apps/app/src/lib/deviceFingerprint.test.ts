// tests device fingerprint
import { beforeEach, describe, expect, it, vi } from 'vitest'

const deviceKeysSupported = vi.fn()
const devicePublicKey = vi.fn()

vi.mock('./deviceKey', () => ({
  deviceKeysSupported: () => deviceKeysSupported(),
  devicePublicKey: () => devicePublicKey(),
}))

import { deviceFingerprint } from './deviceFingerprint'

describe('deviceFingerprint', () => {
  beforeEach(() => {
    deviceKeysSupported.mockReturnValue(true)
    devicePublicKey.mockResolvedValue('spki-public-key')
  })

  it('gives up where the device store is unavailable', async () => {
    deviceKeysSupported.mockReturnValue(false)
    await expect(deviceFingerprint()).resolves.toBeNull()
  })

  it('returns the same mark for the same key', async () => {
    const first = await deviceFingerprint()
    const second = await deviceFingerprint()
    expect(first).toBe(second)
    expect(first).toMatch(/^[0-9a-f]{64}$/)
  })

  it('returns a different mark for a different key', async () => {
    const first = await deviceFingerprint()
    devicePublicKey.mockResolvedValue('another-public-key')
    expect(await deviceFingerprint()).not.toBe(first)
  })

  it('swallows a failure rather than breaking the sign in', async () => {
    devicePublicKey.mockRejectedValue(new Error('store unavailable'))
    await expect(deviceFingerprint()).resolves.toBeNull()
  })
})
