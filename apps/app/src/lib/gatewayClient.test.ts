import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { GatewayClient, parseUserIdFromToken } from './gatewayClient'

vi.mock('@/config/env', () => ({ env: { GATEWAY_URL: 'ws://localhost:8008' } }))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  protocols: string[]
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null
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

  simulateOpen() {
    this.onopen?.()
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }

  simulateClose(code = 1001) {
    this.onclose?.({ code })
  }
}

beforeEach(() => {
  MockWebSocket.instances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('GatewayClient', () => {
  it('connects to correct URL with bearer protocol', () => {
    const client = new GatewayClient('me.user-1', 'my-token')
    client.start()
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8008/ws/me.user-1')
    expect(MockWebSocket.instances[0].protocols).toContain('bearer.my-token')
    client.stop()
  })

  it('emits connected status on open', () => {
    const client = new GatewayClient('me.user-1', 'tok')
    const statuses: string[] = []
    client.onStatus((s) => statuses.push(s))
    client.start()
    MockWebSocket.instances[0].simulateOpen()
    expect(statuses).toContain('connected')
    client.stop()
  })

  it('responds to ping with pong', () => {
    const client = new GatewayClient('me.user-1', 'tok')
    client.start()
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()
    ws.simulateMessage({ type: 'ping' })
    expect(ws.sent).toContain(JSON.stringify({ type: 'pong' }))
    client.stop()
  })

  it('dispatches non-ping messages to handlers', () => {
    const client = new GatewayClient('me.user-1', 'tok')
    const received: unknown[] = []
    client.onMessage((msg) => received.push(msg))
    client.start()
    const ws = MockWebSocket.instances[0]
    ws.simulateOpen()
    ws.simulateMessage({ type: 'audit_event_created', action: 'TICKET_ISSUED' })
    expect(received).toHaveLength(1)
    expect(received[0]).toMatchObject({ type: 'audit_event_created' })
    client.stop()
  })

  it('emits reconnecting status on unexpected close', () => {
    vi.useFakeTimers()
    const client = new GatewayClient('me.user-1', 'tok')
    const statuses: string[] = []
    client.onStatus((s) => statuses.push(s))
    client.start()
    MockWebSocket.instances[0].simulateClose(1001)
    expect(statuses).toContain('reconnecting')
    client.stop()
    vi.useRealTimers()
  })

  it('emits closed on stop', () => {
    const client = new GatewayClient('me.user-1', 'tok')
    const statuses: string[] = []
    client.onStatus((s) => statuses.push(s))
    client.start()
    client.stop()
    expect(statuses).toContain('closed')
  })

  it('does not reconnect after stop', () => {
    vi.useFakeTimers()
    const client = new GatewayClient('me.user-1', 'tok')
    client.start()
    client.stop()
    const countBefore = MockWebSocket.instances.length
    vi.advanceTimersByTime(5_000)
    expect(MockWebSocket.instances.length).toBe(countBefore)
    vi.useRealTimers()
  })
})

describe('parseUserIdFromToken', () => {
  it('extracts sub from a JWT payload', () => {
    const payload = btoa(JSON.stringify({ sub: 'user-abc', type: 'access' }))
    const token = `header.${payload}.sig`
    expect(parseUserIdFromToken(token)).toBe('user-abc')
  })

  it('returns null for malformed token', () => {
    expect(parseUserIdFromToken('not-a-jwt')).toBeNull()
    expect(parseUserIdFromToken('')).toBeNull()
  })

  it('returns null when sub is missing', () => {
    const payload = btoa(JSON.stringify({ type: 'access' }))
    const token = `header.${payload}.sig`
    expect(parseUserIdFromToken(token)).toBeNull()
  })
})
