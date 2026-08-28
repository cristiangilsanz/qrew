// provides use web socket
import { useEffect, useRef, useState } from 'react'

import {
  GatewayClient,
  type GatewayMessage,
  type MessageHandler,
  type WsStatus,
} from '@/lib/gatewayClient'
import { useAuthStore } from '@/store/auth'

export type { WsStatus }

// provides use web socket
export function useWebSocket(channel: string | null, onMessage: MessageHandler) {
  // implements token
  const token = useAuthStore((s) => s.accessToken)
  const [status, setStatus] = useState<WsStatus>('closed')
  const onMessageRef = useRef<MessageHandler>(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!token || !channel) {
      setStatus('closed')
      return
    }

    setStatus('connecting')
    const client = new GatewayClient(channel, token)

    const unsubStatus = client.onStatus(setStatus)
    // implements unsub msg
    const unsubMsg = client.onMessage((msg: GatewayMessage) => onMessageRef.current(msg))

    client.start()

    return () => {
      unsubStatus()
      unsubMsg()
      client.stop()
    }
  }, [channel, token])

  return status
}

// provides use user channel
export function useUserChannel(onMessage: MessageHandler) {
  // implements token
  const token = useAuthStore((s) => s.accessToken)
  const channel = token ? resolveUserChannel(token) : null
  return useWebSocket(channel, onMessage)
}

// implements resolve user channel
function resolveUserChannel(token: string): string | null {
  try {
    const payload = token.split('.')[1]
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as {
      sub?: string
    }
    return decoded.sub ? `me.${decoded.sub}` : null
  } catch {
    return null
  }
}
