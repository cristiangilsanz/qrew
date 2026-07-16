import type { ReactNode } from 'react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { GatewayMessage } from '@/lib/gatewayClient'
import { parseUserIdFromToken } from '@/lib/gatewayClient'
import { useAuthStore } from '@/store/auth'

import { useWebSocket } from './hooks/useWebSocket'

const TICKET_TOASTS: Record<string, string> = {
  TICKET_ISSUED: 'realtime.ticketIssued',
  TICKET_CANCELLED: 'realtime.ticketCancelled',
  TICKET_FROZEN: 'realtime.ticketFrozen',
  PAYMENT_SUCCEEDED: 'realtime.paymentSucceeded',
}

function usePersonalChannel() {
  const token = useAuthStore((s) => s.accessToken)
  return useMemo(() => {
    if (!token) return ''
    const userId = parseUserIdFromToken(token)
    return userId ? `me.${userId}` : ''
  }, [token])
}

function RealtimeConsumer() {
  const { t } = useTranslation()
  const channel = usePersonalChannel()

  const status = useWebSocket(channel, (msg: GatewayMessage) => {
    if (msg.type !== 'audit_event_created') return
    const action = msg.action as string | undefined
    if (!action) return
    const key = TICKET_TOASTS[action]
    if (key) toast.info(t(key))
  })

  if (status === 'reconnecting') {
    toast.warning(t('realtime.reconnecting'), { id: 'ws-reconnecting', duration: Infinity })
  } else if (status === 'connected') {
    toast.dismiss('ws-reconnecting')
  }

  return null
}

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return (
    <>
      {isAuthenticated && <RealtimeConsumer />}
      {children}
    </>
  )
}
