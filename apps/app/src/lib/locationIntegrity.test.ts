// tests the reading of the handset's simulated location flag
import { beforeEach, describe, expect, it, vi } from 'vitest'

const check = vi.fn()
const getPlatform = vi.fn()
const isPluginAvailable = vi.fn()

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    getPlatform: () => getPlatform(),
    isPluginAvailable: (name: string) => isPluginAvailable(name),
  },
  // implements register plugin
  registerPlugin: () => ({ check: () => check() }),
}))

const { readLocationIsMock } = await import('./locationIntegrity')

describe('readLocationIsMock', () => {
  beforeEach(() => {
    check.mockReset()
    getPlatform.mockReturnValue('android')
    isPluginAvailable.mockReturnValue(true)
  })

  it('reports a simulated fix', async () => {
    check.mockResolvedValue({ status: 'mock' })
    await expect(readLocationIsMock()).resolves.toBe(true)
  })

  it('reports a genuine fix', async () => {
    check.mockResolvedValue({ status: 'clean' })
    await expect(readLocationIsMock()).resolves.toBe(false)
  })

  it('sends no signal when the handset has nothing to say', async () => {
    check.mockResolvedValue({ status: 'unknown' })
    await expect(readLocationIsMock()).resolves.toBeNull()
  })

  it('sends no signal from the browser', async () => {
    getPlatform.mockReturnValue('web')
    await expect(readLocationIsMock()).resolves.toBeNull()
    expect(check).not.toHaveBeenCalled()
  })

  it('sends no signal from a platform without the plugin', async () => {
    getPlatform.mockReturnValue('ios')
    isPluginAvailable.mockReturnValue(false)
    await expect(readLocationIsMock()).resolves.toBeNull()
    expect(check).not.toHaveBeenCalled()
  })

  it('sends no signal when the plugin fails', async () => {
    check.mockRejectedValue(new Error('boom'))
    await expect(readLocationIsMock()).resolves.toBeNull()
  })
})
