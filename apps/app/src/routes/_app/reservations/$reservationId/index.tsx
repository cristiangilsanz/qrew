// implements reservation id
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { CheckCircle2, ChevronDown, Clock, CreditCard, Loader2, Save } from 'lucide-react'
import { Suspense, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { NotFound } from '@/components/ui/not-found'
import { PageError } from '@/components/ui/page-error'
import { ReservationSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { ticketsApi } from '@/features/tickets/api'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { useInitiatePayment } from '@/features/tickets/hooks/useInitiatePayment'
import { useReservation } from '@/features/tickets/hooks/useReservation'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { DOCUMENT_TYPES, type DocumentType, isValidDocument } from '@/lib/documents'
import { isNotFound } from '@/lib/errors'
import { fieldErrorMessage } from '@/lib/errors'
import { lazyWithReload } from '@/lib/lazyWithReload'

// renders the stripe checkout component
const StripeCheckout = lazyWithReload(() =>
  import('@/features/tickets/components/StripeCheckout').then((m) => ({
    default: m.StripeCheckout,
  })),
)

export const Route = createFileRoute('/_app/reservations/$reservationId/')({
  component: ReservationPage,
})

// implements format seconds
function formatSeconds(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

// implements format price
function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

// renders the reservation page component
function ReservationPage() {
  const { t } = useTranslation()
  const { reservationId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [holders, setHolders] = useState<
    Array<{ holder_name: string; holder_document_type: DocumentType; holder_dni: string }>
  >([])
  const [holdersSaved, setHoldersSaved] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const {
    data: reservation,
    isLoading: reservationLoading,
    isError,
    error,
    refetch,
  } = useReservation(reservationId, !!clientSecret)
  const { data: event, isLoading: eventLoading } = useEvent(reservation?.event_id ?? '')
  const { data: myTickets } = useTickets(confirming)

  // implements initiate payment
  const initiatePayment = useInitiatePayment((payment) => {
    setClientSecret(payment.client_secret)
  })

  const saveHolders = useMutation({
    // implements mutation fn
    mutationFn: () =>
      ticketsApi.setHolders(
        reservationId,
        holders.map((h, i) => ({
          position: i + 1,
          holder_name: h.holder_name,
          holder_document_type: h.holder_document_type,
          holder_dni: h.holder_dni,
        })),
      ),
    // handles on success
    onSuccess: () => setHoldersSaved(true),
    // handles on error
    onError: (err) => {
      toast.error(fieldErrorMessage(err) ?? t('tickets.reservation.holdersFailed'))
    },
  })

  const countdown = useCountdown(reservation?.expires_at)

  // handles handle pay success
  const handlePaySuccess = () => {
    setConfirming(true)
  }

  const ticketsIssued =
    myTickets?.some((tk) => tk.reservation_id === reservationId && tk.state !== 'reserved') ?? false

  useEffect(() => {
    if (!confirming) return

    // closes the wait and hands the user their tickets
    const finish = () => {
      toast.success(t('tickets.payment.success'))
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      void navigate({ to: '/tickets' })
    }

    if (ticketsIssued) {
      finish()
      return
    }
    const timer = setTimeout(finish, 20_000)
    return () => clearTimeout(timer)
  }, [confirming, ticketsIssued, navigate, queryClient, t])

  const isLoading = reservationLoading || (!!reservation && eventLoading)
  if (isLoading) return <ReservationSkeleton />

  if (isError && !isNotFound(error)) {
    return <PageError onRetry={() => void refetch()} />
  }

  if (isError || !reservation) {
    return <NotFound message={t('common.resourceGone')} />
  }

  const quantity = reservation.quantity
  const initializedHolders =
    holders.length === quantity
      ? holders
      : Array.from(
          { length: quantity },
          (_, i) => holders[i] ?? { holder_name: '', holder_document_type: 'dni', holder_dni: '' },
        )

  // implements update holder
  const updateHolder = (
    index: number,
    field: 'holder_name' | 'holder_document_type' | 'holder_dni',
    value: string,
  ) => {
    // implements next
    const next = initializedHolders.map((h, i) => (i === index ? { ...h, [field]: value } : h))
    setHolders(next)
    setHoldersSaved(false)
  }

  // implements holders complete
  const holdersComplete = initializedHolders.every(
    (h) => h.holder_name.trim().length > 0 && isValidDocument(h.holder_dni, h.holder_document_type),
  )

  // implements order lines
  const lines = reservation.items.map((item) => {
    const tier = event?.ticket_types.find((tt) => tt.id === item.ticket_type_id)
    return {
      id: item.ticket_type_id,
      name: tier?.name ?? '—',
      quantity: item.quantity,
      subtotal: (tier?.price_cents ?? 0) * item.quantity,
      currency: tier?.currency ?? 'EUR',
    }
  })
  const currency = lines[0]?.currency ?? 'EUR'
  const totalPrice = lines.reduce((sum, line) => sum + line.subtotal, 0)

  const isPaid = reservation.status === 'paid'
  const isExpired = reservation.status === 'expired'
  const countdownExpired = countdown === 0
  const isCancelled = reservation.status === 'cancelled'
  const canPay =
    !isPaid && !isExpired && !countdownExpired && !isCancelled && !clientSecret && holdersSaved

  return (
    <div className="mx-auto max-w-[430px] px-4 pt-5 pb-28">
      <BackButton to="/tickets" className="mb-6" />

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

      <div className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5">
        <div>
          <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">
            {event?.name ?? '—'}
          </p>
          <h2 className="text-lg leading-tight font-bold">{t('tickets.reservation.title')}</h2>
        </div>

        <div className="border-t border-white/10" />

        <div className="space-y-2.5">
          {lines.map((line) => (
            <div key={line.id} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                {line.name} <span className="text-white/40">x{line.quantity}</span>
              </span>
              <span className="font-semibold">{formatPrice(line.subtotal, line.currency)}</span>
            </div>
          ))}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t('tickets.checkout.quantity')}</span>
            <span className="font-semibold">{quantity}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-semibold">Total</span>
            <span className="text-primary text-lg font-bold">
              {formatPrice(totalPrice, currency)}
            </span>
          </div>
        </div>
      </div>

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
                <div className="flex gap-2">
                  <div className="relative shrink-0">
                    <select
                      value={holder.holder_document_type}
                      onChange={(e) => updateHolder(i, 'holder_document_type', e.target.value)}
                      className="w-full appearance-none rounded-xl border border-white/10 bg-white/5 py-2.5 pr-9 pl-3 text-sm text-white focus:border-white/30 focus:outline-none"
                    >
                      {DOCUMENT_TYPES.map((type) => (
                        <option key={type} value={type} className="bg-[hsl(0,0%,10%)]">
                          {t(`tickets.holders.documentType.${type}`)}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="text-muted-foreground pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2" />
                  </div>
                  <input
                    type="text"
                    placeholder={t(
                      `tickets.holders.documentPlaceholder.${holder.holder_document_type}`,
                    )}
                    value={holder.holder_dni}
                    onChange={(e) => updateHolder(i, 'holder_dni', e.target.value)}
                    className={`placeholder:text-muted-foreground w-full rounded-xl border bg-white/5 px-4 py-2.5 text-sm text-white focus:outline-none ${
                      holder.holder_dni &&
                      !isValidDocument(holder.holder_dni, holder.holder_document_type)
                        ? 'border-red-500/60 focus:border-red-500/80'
                        : 'border-white/10 focus:border-white/30'
                    }`}
                  />
                </div>
                {holder.holder_dni &&
                  !isValidDocument(holder.holder_dni, holder.holder_document_type) && (
                    <p className="mt-1 px-1 text-xs text-red-400">
                      {t(`tickets.holders.invalid.${holder.holder_document_type}`)}
                    </p>
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
              <Save className="h-4 w-4" />
              Save
            </button>
          </div>
        </div>
      )}

      {clientSecret && !confirming && (
        <div className="mt-6">
          <Suspense fallback={null}>
            <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaySuccess} />
          </Suspense>
        </div>
      )}

      {confirming && (
        <div className="mt-6 flex flex-col items-center gap-3 py-10 text-center">
          <Loader2 className="text-primary h-8 w-8 animate-spin" />
          <p className="text-muted-foreground text-sm">{t('tickets.payment.confirming')}</p>
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

      {canPay && (
        <div className="keyboard-hide fixed inset-x-0 bottom-24 z-40">
          <div className="mx-auto flex w-full max-w-[430px] justify-end bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent px-4 pt-8">
            <button
              onClick={() => initiatePayment.mutate(reservationId)}
              disabled={initiatePayment.isPending}
              className="bg-primary flex h-12 items-center gap-2 rounded-full px-6 text-sm font-semibold text-white shadow-lg disabled:opacity-50"
            >
              <CreditCard className="h-4 w-4" />
              Pay Now
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
