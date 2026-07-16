import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useWebSocket } from './useWebSocket'

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector: (s: { accessToken: string }) => unknown) =>
    selector({ accessToken: 'test.eyJzdWIiOiJ1c2VyLTEifQ.sig' }),
}))

vi.mock('@/config/env', () => ({
  env: { GATEWAY_URL: 'ws://localhost:8008' },
}))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  protocols: string[]
  onopen: (() => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  sent: string[] = []

  constructor(url: string, protocols?: string[]) {
    this.url = url
    this.protocols = protocols ?? []
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close(code = 1000) {
    this.onclose?.({ code })
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('connects with the correct URL and bearer subprotocol', () => {
    renderHook(() => useWebSocket('me.user-1', vi.fn()))

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8008/ws/me.user-1')
    expect(MockWebSocket.instances[0].protocols).toContain('bearer.test.eyJzdWIiOiJ1c2VyLTEifQ.sig')
  })

  it('transitions to connected status on open', async () => {
    const { result } = renderHook(() => useWebSocket('me.user-1', vi.fn()))

    await act(async () => {
      MockWebSocket.instances[0].onopen?.()
    })

    expect(result.current).toBe('connected')
  })

  it('responds to ping messages with pong', async () => {
    renderHook(() => useWebSocket('me.user-1', vi.fn()))
    const ws = MockWebSocket.instances[0]

    await act(async () => {
      ws.onopen?.()
      ws.onmessage?.({ data: JSON.stringify({ type: 'ping' }) })
    })

    expect(ws.sent).toContain(JSON.stringify({ type: 'pong' }))
  })

  it('calls onMessage handler for non-ping events', async () => {
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('me.user-1', onMessage))
    const ws = MockWebSocket.instances[0]

    await act(async () => {
      ws.onopen?.()
      ws.onmessage?.({
        data: JSON.stringify({
          type: 'ticket.state_changed',
          ticket_id: 'abc-123',
          state: 'issued',
        }),
      })
    })

    expect(onMessage).toHaveBeenCalledWith({
      type: 'ticket.state_changed',
      ticket_id: 'abc-123',
      state: 'issued',
    })
  })

  it('schedules reconnect after unexpected close and does not reconnect after clean unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket('me.user-1', vi.fn()))
    const ws = MockWebSocket.instances[0]

    await act(async () => {
      ws.onopen?.()
      ws.onclose?.({ code: 1006 })
    })

    expect(MockWebSocket.instances).toHaveLength(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_100)
    })

    expect(MockWebSocket.instances).toHaveLength(2)

    unmount()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })

    expect(MockWebSocket.instances).toHaveLength(2)
  })
})
