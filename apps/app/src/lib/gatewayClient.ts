import { env } from '@/config/env'

export type GatewayMessage = Record<string, unknown>
export type MessageHandler = (msg: GatewayMessage) => void
export type WsStatus = 'connecting' | 'connected' | 'reconnecting' | 'closed'
export type StatusHandler = (status: WsStatus) => void

const RECONNECT_BASE_MS = 1_000
const RECONNECT_MAX_MS = 30_000
const RECONNECT_FACTOR = 2

export class GatewayClient {
  private ws: WebSocket | null = null
  private messageHandlers = new Set<MessageHandler>()
  private statusHandlers = new Set<StatusHandler>()
  private stopped = false
  private attempt = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  constructor(
    private readonly channel: string,
    private readonly token: string,
  ) {}

  start(): void {
    this.stopped = false
    this._connect()
  }

  stop(): void {
    this.stopped = true
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close(1000, 'client stop')
    this.ws = null
    this._emitStatus('closed')
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler)
    return () => this.statusHandlers.delete(handler)
  }

  private _emitStatus(status: WsStatus): void {
    for (const h of this.statusHandlers) h(status)
  }

  _connect(): void {
    if (this.stopped) return
    const url = `${env.GATEWAY_URL}/ws/${this.channel}`
    const ws = new WebSocket(url, [`bearer.${this.token}`])
    this.ws = ws

    ws.onopen = () => {
      this.attempt = 0
      this._emitStatus('connected')
    }

    ws.onmessage = (event) => {
      let msg: GatewayMessage
      try {
        msg = JSON.parse(event.data as string) as GatewayMessage
      } catch {
        return
      }
      if (msg.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }))
        return
      }
      for (const h of this.messageHandlers) h(msg)
    }

    ws.onclose = (event) => {
      if (this.stopped || event.code === 1000) return
      this._emitStatus('reconnecting')
      this._scheduleReconnect()
    }

    ws.onerror = () => {
      // onclose fires after onerror, reconnect handled there
    }
  }

  private _scheduleReconnect(): void {
    if (this.stopped) return
    const delay = Math.min(RECONNECT_BASE_MS * RECONNECT_FACTOR ** this.attempt, RECONNECT_MAX_MS)
    this.attempt++
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this._connect()
    }, delay)
  }
}

export function parseUserIdFromToken(token: string): string | null {
  try {
    const payload = token.split('.')[1]
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as {
      sub?: string
    }
    return decoded.sub ?? null
  } catch {
    return null
  }
}
