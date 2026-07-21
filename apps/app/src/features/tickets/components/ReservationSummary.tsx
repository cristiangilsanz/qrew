import { Clock, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

import type { Reservation } from '../api'
import { useCancelReservation } from '../hooks/useCancelReservation'

interface Props {
  reservation: Reservation
  onCancel?: () => void
  onPay?: () => void
  payLoading?: boolean
}

function useCountdown(expiresAt: string) {
  const [remaining, setRemaining] = useState(() =>
    Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000)),
  )

  useEffect(() => {
    if (remaining <= 0) return
    const id = setInterval(() => {
      setRemaining((s) => {
        if (s <= 1) {
          clearInterval(id)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [remaining, expiresAt])

  return remaining
}

function formatSeconds(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export function ReservationSummary({ reservation, onCancel, onPay, payLoading }: Props) {
  const { t } = useTranslation()
  const remaining = useCountdown(reservation.expires_at)
  const cancel = useCancelReservation(reservation.id, onCancel)

  const isExpired = remaining === 0 || reservation.status === 'expired'
  const isCancelled = reservation.status === 'cancelled'
  const isPaid = reservation.status === 'paid'
  const canAct = !isExpired && !isCancelled && !isPaid

  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground text-sm">{t('tickets.reservation.quantity')}</span>
          <span className="font-semibold">{reservation.quantity}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground text-sm">{t('tickets.reservation.status')}</span>
          <span className="font-semibold capitalize">{reservation.status}</span>
        </div>

        {canAct && (
          <div className="flex items-center gap-2">
            <Clock className="text-destructive h-4 w-4 shrink-0" />
            <span
              className={`font-mono text-sm font-semibold ${remaining < 60 ? 'text-destructive' : ''}`}
            >
              {formatSeconds(remaining)}
            </span>
            <span className="text-muted-foreground text-xs">
              {t('tickets.reservation.expiresIn')}
            </span>
          </div>
        )}

        {isExpired && !isPaid && (
          <p className="text-destructive text-sm">{t('tickets.reservation.expired')}</p>
        )}
        {isCancelled && (
          <p className="text-muted-foreground text-sm">{t('tickets.reservation.cancelled')}</p>
        )}
        {isPaid && (
          <p className="text-sm font-medium text-green-600">{t('tickets.reservation.paid')}</p>
        )}

        {canAct && (
          <div className="flex flex-col gap-3">
            <Button className="w-full" onClick={onPay} isLoading={payLoading}>
              {t('tickets.payment.payButton')}
            </Button>
            <button
              onClick={() => cancel.mutate()}
              disabled={cancel.isPending}
              className="flex w-full items-center gap-3 rounded-2xl bg-red-500 px-4 py-3 text-left text-white transition-colors hover:bg-red-600 disabled:opacity-50"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/20">
                {cancel.isPending ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
              </div>
              <span className="text-sm font-semibold">{t('tickets.reservation.cancelButton')}</span>
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
