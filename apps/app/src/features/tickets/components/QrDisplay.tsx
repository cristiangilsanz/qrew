import { Loader2, QrCode, ShieldX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import QRCode from 'react-qr-code'

import { Button } from '@/components/ui/button'
import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

interface Props {
  ticketId: string
}

type QrState =
  | { status: 'idle' }
  | { status: 'locating' }
  | { status: 'streaming'; jwt: string; expiresAt: string }
  | { status: 'denied'; reason: string }
  | { status: 'error' }

function useCountdown(targetIso: string | null): number {
  const [secondsLeft, setSecondsLeft] = useState(0)
  useEffect(() => {
    if (!targetIso) return
    const update = () => {
      const diff = Math.max(0, Math.floor((new Date(targetIso).getTime() - Date.now()) / 1000))
      setSecondsLeft(diff)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [targetIso])
  return secondsLeft
}

export function QrDisplay({ ticketId }: Props) {
  const { t } = useTranslation()
  const [state, setState] = useState<QrState>({ status: 'idle' })
  const abortRef = useRef<AbortController | null>(null)
  const expiresAt = state.status === 'streaming' ? state.expiresAt : null
  const secondsLeft = useCountdown(expiresAt)

  const startStream = () => {
    setState({ status: 'locating' })
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setState((prev) => (prev.status === 'locating' ? { status: 'locating' } : prev))
        openStream(pos.coords.latitude, pos.coords.longitude)
      },
      () => setState({ status: 'denied', reason: 'geolocation' }),
      { timeout: 10_000 },
    )
  }

  const openStream = (latitude: number, longitude: number) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    const token = useAuthStore.getState().accessToken
    setState({ status: 'locating' })

    fetch(`${env.TICKETING_URL}/v1/tickets/${ticketId}/qr/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ latitude, longitude }),
      signal: ctrl.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          const field = (data?.detail as { field?: string } | undefined)?.field ?? 'unknown'
          setState({ status: 'denied', reason: field })
          return
        }
        const reader = res.body?.getReader()
        if (!reader) return
        const decoder = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() ?? ''
          for (const part of parts) {
            const eventLine = part.split('\n').find((l) => l.startsWith('event:'))
            const dataLine = part.split('\n').find((l) => l.startsWith('data:'))
            if (!eventLine || !dataLine) continue
            const eventType = eventLine.replace('event:', '').trim()
            const payload = JSON.parse(dataLine.replace('data:', '').trim())
            if (eventType === 'qr') {
              setState({ status: 'streaming', jwt: payload.jwt, expiresAt: payload.expires_at })
            } else if (eventType === 'denied') {
              setState({ status: 'denied', reason: payload.detail?.field ?? 'unknown' })
              return
            }
          }
        }
      })
      .catch((err) => {
        if ((err as Error).name !== 'AbortError') setState({ status: 'error' })
      })
  }

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [ticketId])

  if (state.status === 'idle') {
    return (
      <div className="flex h-[300px] flex-col items-center justify-center gap-4">
        <div className="relative">
          <div className="opacity-40 blur-md">
            <QRCode value="qrew-placeholder-blurred" size={200} />
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Button onClick={startStream} className="rounded-full px-6 shadow-lg">
              <QrCode className="h-4 w-4" />
              {t('tickets.qr.showButton')}
            </Button>
          </div>
        </div>
        {/* spacer to match countdown text height */}
        <div className="h-10" />
      </div>
    )
  }

  if (state.status === 'locating') {
    return (
      <div className="flex h-[300px] flex-col items-center justify-center gap-3">
        <Loader2 className="text-primary h-8 w-8 animate-spin" />
        <p className="text-muted-foreground text-sm">{t('tickets.qr.locating')}</p>
      </div>
    )
  }

  if (state.status === 'denied') {
    const key =
      state.reason === 'geolocation'
        ? 'tickets.qr.deniedLocation'
        : state.reason === 'geofence'
          ? 'tickets.qr.deniedGeofence'
          : state.reason === 'attestation'
            ? 'tickets.qr.deniedAttestation'
            : state.reason === 'state'
              ? 'tickets.qr.deniedState'
              : 'tickets.qr.denied'
    return (
      <div className="flex h-[300px] flex-col items-center justify-center gap-4 text-center">
        <ShieldX className="text-destructive h-10 w-10" />
        <p className="text-destructive text-sm font-medium">{t(key)}</p>
        <Button variant="outline" onClick={startStream}>
          {t('tickets.qr.retry')}
        </Button>
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="flex h-[300px] flex-col items-center justify-center gap-4 text-center">
        <ShieldX className="text-destructive h-10 w-10" />
        <p className="text-muted-foreground text-sm">{t('tickets.qr.error')}</p>
        <Button variant="outline" onClick={startStream}>
          {t('tickets.qr.retry')}
        </Button>
      </div>
    )
  }

  const mins = String(Math.floor(secondsLeft / 60)).padStart(2, '0')
  const secs = String(secondsLeft % 60).padStart(2, '0')

  return (
    <div className="flex h-[300px] flex-col items-center justify-center gap-4">
      <div className="rounded-2xl bg-white p-4 shadow-md">
        <QRCode value={state.jwt} size={200} />
      </div>
      {/* Countdown to next rotation */}
      <div className="flex flex-col items-center gap-0.5">
        <p className="font-mono text-2xl font-bold text-gray-900 tabular-nums">
          {mins}:{secs}
        </p>
        <p className="text-xs text-gray-400">
          Rotates at{' '}
          {new Date(state.expiresAt).toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })}
        </p>
      </div>
    </div>
  )
}
