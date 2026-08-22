import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listeners: ((status: { connected: boolean }) => void)[] = []
const remove = vi.fn()
const getStatus = vi.fn()

vi.mock('@capacitor/network', () => ({
  Network: {
    getStatus: () => getStatus(),
    addListener: (_event: string, handler: (status: { connected: boolean }) => void) => {
      listeners.push(handler)
      return Promise.resolve({ remove })
    },
  },
}))

const { useNetwork } = await import('./useNetwork')

describe('useNetwork', () => {
  beforeEach(() => {
    listeners.length = 0
    remove.mockClear()
    getStatus.mockReset()
    getStatus.mockResolvedValue({ connected: true })
  })

  it('starts from the status the device reports', async () => {
    getStatus.mockResolvedValue({ connected: false })
    const { result } = renderHook(() => useNetwork())
    await act(async () => {})
    expect(result.current.isOnline).toBe(false)
  })

  it('follows the changes the device announces', async () => {
    const { result } = renderHook(() => useNetwork())
    await act(async () => {})
    expect(result.current.isOnline).toBe(true)

    await act(async () => {
      listeners[0]?.({ connected: false })
    })
    expect(result.current.isOnline).toBe(false)

    await act(async () => {
      listeners[0]?.({ connected: true })
    })
    expect(result.current.isOnline).toBe(true)
  })

  it('drops the listener when the component goes away', async () => {
    const { unmount } = renderHook(() => useNetwork())
    await act(async () => {})
    unmount()
    await act(async () => {})
    expect(remove).toHaveBeenCalled()
  })
})
