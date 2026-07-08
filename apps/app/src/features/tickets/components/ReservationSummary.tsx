import { Clock } from 'lucide-react'
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
          <div className="flex gap-2">
            <Button className="flex-1" onClick={onPay} isLoading={payLoading}>
              {t('tickets.payment.payButton')}
            </Button>
            <Button
              variant="outline"
              onClick={() => cancel.mutate()}
              isLoading={cancel.isPending}
              className="flex-1"
            >
              {t('tickets.reservation.cancelButton')}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
