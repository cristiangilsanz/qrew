import { Geolocation } from '@capacitor/geolocation'
import { Loader2, MapPin, QrCode, RefreshCw, ShieldX } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
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
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const activeRef = useRef(false)
  const expiresAt = state.status === 'streaming' ? state.expiresAt : null
  const secondsLeft = useCountdown(expiresAt)

  const fetchQr = useCallback(
    async (latitude: number, longitude: number) => {
      if (!activeRef.current) return
      const token = useAuthStore.getState().accessToken
      try {
        const res = await fetch(
          `${env.API_URL}/api/ticketing/v1/tickets/${ticketId}/qr?latitude=${latitude}&longitude=${longitude}`,
          {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
          },
        )
        if (!activeRef.current) return
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          const field = (data?.detail as { field?: string } | undefined)?.field ?? 'unknown'
          setState({ status: 'denied', reason: field })
          return
        }
        const data = await res.json()
        setState({ status: 'streaming', jwt: data.jwt, expiresAt: data.expires_at })

        // Schedule refresh ~3s before expiry
        const msUntilExpiry = new Date(data.expires_at).getTime() - Date.now()
        const refreshIn = Math.max(1000, msUntilExpiry - 3000)
        refreshTimerRef.current = setTimeout(() => {
          void fetchQr(latitude, longitude)
        }, refreshIn)
      } catch {
        if (activeRef.current) setState({ status: 'error' })
      }
    },
    [ticketId],
  )

  const startStream = async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    activeRef.current = true
    setState({ status: 'locating' })
    try {
      await Geolocation.requestPermissions()
      const pos = await Geolocation.getCurrentPosition({ timeout: 20000, maximumAge: 60000 })
      await fetchQr(pos.coords.latitude, pos.coords.longitude)
    } catch {
      if (activeRef.current) setState({ status: 'denied', reason: 'geolocation' })
    }
  }

  useEffect(() => {
    return () => {
      activeRef.current = false
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    }
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
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
          <Loader2 className="text-primary h-6 w-6 animate-spin" />
        </div>
        <p className="text-xs text-gray-400">{t('tickets.qr.locating')}</p>
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
    const isLocation = state.reason === 'geolocation'
    return (
      <div className="flex h-[300px] flex-col items-center justify-center gap-3 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
          {isLocation ? (
            <MapPin className="h-6 w-6 text-red-400" />
          ) : (
            <ShieldX className="h-6 w-6 text-red-400" />
          )}
        </div>
        <p className="text-xs text-gray-400">{t(key)}</p>
        <button
          onClick={startStream}
          className="bg-primary mt-1 flex items-center gap-2 rounded-full px-6 py-2.5 text-sm font-semibold text-white"
        >
          <RefreshCw className="h-4 w-4 shrink-0" />
          {t('tickets.qr.retry')}
        </button>
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="flex h-[300px] flex-col items-center justify-center gap-3 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
          <QrCode className="h-6 w-6 text-red-400" />
        </div>
        <p className="text-xs text-gray-400">{t('tickets.qr.error')}</p>
        <button
          onClick={startStream}
          className="bg-primary mt-1 flex items-center gap-2 rounded-full px-6 py-2.5 text-sm font-semibold text-white"
        >
          <RefreshCw className="h-4 w-4 shrink-0" />
          {t('tickets.qr.retry')}
        </button>
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
