import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import axios from 'axios'
import { CheckCircle2, Clock, CreditCard, Save } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ReservationSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { ticketsApi } from '@/features/tickets/api'
import { StripeCheckout } from '@/features/tickets/components/StripeCheckout'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { useInitiatePayment } from '@/features/tickets/hooks/useInitiatePayment'
import { useReservation } from '@/features/tickets/hooks/useReservation'

export const Route = createFileRoute('/_app/reservations/$reservationId/')({
  component: ReservationPage,
})

function formatSeconds(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

function ReservationPage() {
  const { t } = useTranslation()
  const { reservationId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [holders, setHolders] = useState<Array<{ holder_name: string; holder_dni: string }>>([])
  const [holdersSaved, setHoldersSaved] = useState(false)

  const {
    data: reservation,
    isLoading: reservationLoading,
    isError,
  } = useReservation(reservationId, !!clientSecret)
  const { data: event, isLoading: eventLoading } = useEvent(reservation?.event_id ?? '')

  const initiatePayment = useInitiatePayment((payment) => {
    setClientSecret(payment.client_secret)
  })

  const saveHolders = useMutation({
    mutationFn: () =>
      ticketsApi.setHolders(
        reservationId,
        holders.map((h, i) => ({
          position: i + 1,
          holder_name: h.holder_name,
          holder_dni: h.holder_dni,
        })),
      ),
    onSuccess: () => setHoldersSaved(true),
    onError: (err) => {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined
      const message =
        typeof detail === 'object' && detail?.message
          ? detail.message
          : typeof detail === 'string'
            ? detail
            : 'Failed to save holder info'
      toast.error(message)
    },
  })

  const countdown = useCountdown(reservation?.expires_at)

  const handlePaySuccess = () => {
    toast.success(t('tickets.payment.success'))
    void queryClient.invalidateQueries({ queryKey: ['tickets'] })
    void navigate({ to: '/tickets' })
  }

  const isLoading = reservationLoading || (!!reservation && eventLoading)
  if (isLoading) return <ReservationSkeleton />

  if (isError || !reservation) {
    return (
      <div className="mx-auto max-w-md p-6">
        <p className="text-muted-foreground">{t('tickets.reservation.notFound')}</p>
      </div>
    )
  }

  const quantity = reservation.quantity
  const initializedHolders =
    holders.length === quantity
      ? holders
      : Array.from(
          { length: quantity },
          (_, i) => holders[i] ?? { holder_name: '', holder_dni: '' },
        )

  const updateHolder = (index: number, field: 'holder_name' | 'holder_dni', value: string) => {
    const next = initializedHolders.map((h, i) => (i === index ? { ...h, [field]: value } : h))
    setHolders(next)
    setHoldersSaved(false)
  }

  const validateDni = (dni: string): boolean => {
    const v = dni.trim().toUpperCase()
    const letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    const dniRe = /^\d{8}[A-Z]$/
    const nieRe = /^[XYZ]\d{7}[A-Z]$/
    if (dniRe.test(v)) return letters[parseInt(v.slice(0, 8)) % 23] === v[8]
    if (nieRe.test(v)) {
      const prefix: Record<string, string> = { X: '0', Y: '1', Z: '2' }
      const digits = prefix[v[0]] + v.slice(1, 8)
      return letters[parseInt(digits) % 23] === v[8]
    }
    return false
  }

  const holdersComplete = initializedHolders.every(
    (h) => h.holder_name.trim().length > 0 && validateDni(h.holder_dni),
  )

  const ticketType = event?.ticket_types.find((tt) => tt.id === reservation.ticket_type_id)
  const unitPrice = ticketType?.price_cents ?? 0
  const currency = ticketType?.currency ?? 'EUR'
  const totalPrice = unitPrice * quantity

  const isPaid = reservation.status === 'paid'
  const isExpired = reservation.status === 'expired'
  const countdownExpired = countdown === 0
  const isCancelled = reservation.status === 'cancelled'
  const canPay =
    !isPaid && !isExpired && !countdownExpired && !isCancelled && !clientSecret && holdersSaved

  return (
    <div className="mx-auto min-h-screen max-w-[430px] px-4 pt-5 pb-28">
      <BackButton onClick={() => void navigate({ to: '/tickets' })} className="mb-6" />

      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">Complete your order</h1>
        {!isPaid && !isCancelled && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 shrink-0 text-yellow-400" />
            {isExpired || countdownExpired ? (
              <span className="text-destructive text-sm font-semibold">Expired</span>
            ) : (
              <>
                <span
                  className={`font-mono text-sm font-semibold ${countdown < 60 ? 'text-destructive' : 'text-yellow-400'}`}
                >
                  {formatSeconds(countdown)}
                </span>
                <span className="text-muted-foreground text-xs">remaining</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Order summary card */}
      <div className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5">
        <div>
          <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">
            {event?.name ?? '—'}
          </p>
          <h2 className="text-lg leading-tight font-bold">{ticketType?.name ?? '—'}</h2>
          {ticketType?.description && (
            <p className="text-muted-foreground mt-1 text-sm">{ticketType.description}</p>
          )}
        </div>

        <div className="border-t border-white/10" />

        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Quantity</span>
            <span className="font-semibold">{quantity}</span>
          </div>
          {unitPrice > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Unit price</span>
              <span className="font-semibold">{formatPrice(unitPrice, currency)}</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="font-semibold">Total</span>
            <span className="text-primary text-lg font-bold">
              {formatPrice(totalPrice, currency)}
            </span>
          </div>
        </div>
      </div>

      {/* Holder info — only shown when reservation is still open */}
      {!isPaid && !isCancelled && !clientSecret && (
        <div className="mt-4 space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">Who&apos;s attending?</p>
            {holdersSaved && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Saved
              </span>
            )}
          </div>

          {initializedHolders.map((holder, i) => (
            <div key={i} className="space-y-2">
              {quantity > 1 && (
                <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                  Ticket {i + 1}
                </p>
              )}
              <input
                type="text"
                placeholder="Full name"
                value={holder.holder_name}
                onChange={(e) => updateHolder(i, 'holder_name', e.target.value)}
                className="placeholder:text-muted-foreground w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-white/30 focus:outline-none"
              />
              <div>
                <input
                  type="text"
                  placeholder="DNI / NIE"
                  value={holder.holder_dni}
                  onChange={(e) => updateHolder(i, 'holder_dni', e.target.value)}
                  className={`placeholder:text-muted-foreground w-full rounded-xl border bg-white/5 px-4 py-2.5 text-sm text-white focus:outline-none ${
                    holder.holder_dni && !validateDni(holder.holder_dni)
                      ? 'border-red-500/60 focus:border-red-500/80'
                      : 'border-white/10 focus:border-white/30'
                  }`}
                />
                {holder.holder_dni && !validateDni(holder.holder_dni) && (
                  <p className="mt-1 px-1 text-xs text-red-400">Invalid DNI / NIE</p>
                )}
              </div>
            </div>
          ))}

          <div className="flex justify-end">
            <button
              onClick={() => saveHolders.mutate()}
              disabled={!holdersComplete || saveHolders.isPending}
              className="bg-primary flex h-10 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white shadow-lg transition-opacity disabled:opacity-40"
            >
              {saveHolders.isPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save
            </button>
          </div>
        </div>
      )}

      {/* Stripe form */}
      {clientSecret && (
        <div className="mt-6">
          <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaySuccess} />
        </div>
      )}

      {isPaid && (
        <p className="mt-6 text-center text-sm font-medium text-green-500">
          {t('tickets.reservation.paid')}
        </p>
      )}
      {isExpired && (
        <p className="text-destructive mt-6 text-center text-sm">
          {t('tickets.reservation.expired')}
        </p>
      )}
      {isCancelled && (
        <p className="text-muted-foreground mt-6 text-center text-sm">
          {t('tickets.reservation.cancelled')}
        </p>
      )}

      {/* Pay Now — fixed bottom right, only enabled after holders are saved */}
      {canPay && (
        <div className="fixed inset-x-0 bottom-24 z-40">
          <div className="mx-auto flex max-w-[430px] justify-end bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent px-4 pt-8 pb-5">
            <button
              onClick={() => initiatePayment.mutate(reservationId)}
              disabled={initiatePayment.isPending}
              className="bg-primary flex h-12 items-center gap-2 rounded-full px-6 text-sm font-semibold text-white shadow-lg disabled:opacity-50"
            >
              {initiatePayment.isPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <CreditCard className="h-4 w-4" />
              )}
              Pay Now
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
