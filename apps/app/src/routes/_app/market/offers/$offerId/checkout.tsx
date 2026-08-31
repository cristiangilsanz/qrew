// implements the checkout that names the holder of a resold ticket and takes the payment
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ChevronDown, Clock, CreditCard, Loader2 } from 'lucide-react'
import { Suspense, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { PageError } from '@/components/ui/page-error'
import { Skeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketOffer } from '@/features/market/hooks/useMarketOffer'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { DOCUMENT_TYPES, type DocumentType, isValidDocument } from '@/lib/documents'
import { toastErrorMessage } from '@/lib/errors'
import { lazyWithReload } from '@/lib/lazyWithReload'
import { cn } from '@/lib/utils'

const StripeCheckout = lazyWithReload(() =>
  import('@/features/tickets/components/StripeCheckout').then((m) => ({
    default: m.StripeCheckout,
  })),
)

export const Route = createFileRoute('/_app/market/offers/$offerId/checkout')({
  component: OfferCheckoutPage,
})

// formats a countdown as minutes and seconds
function formatSeconds(s: number): string {
  const m = Math.floor(s / 60)
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

// formats an amount in cents for display
function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

// walks the buyer through naming the holder and paying for the offer they accepted
function OfferCheckoutPage() {
  const { t } = useTranslation()
  const { offerId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: offer, isLoading, isError, refetch } = useMarketOffer(offerId)
  const { data: event } = useEvent(offer?.event_id ?? '')
  const countdown = useCountdown(offer?.state === 'pending' ? offer.expires_at : null)

  const [holderName, setHolderName] = useState('')
  const [documentType, setDocumentType] = useState<DocumentType>('dni')
  const [documentNumber, setDocumentNumber] = useState('')
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const ticketsBeforePay = useRef<Set<string>>(new Set())
  const { data: myTickets } = useTickets(confirming)

  const pay = useMutation({
    // names the holder the ticket transfers to before asking stripe for the money
    mutationFn: async () => {
      await marketApi.setHolders(offerId, holderName.trim(), documentNumber, documentType)
      return marketApi.initiateOfferPayment(offerId)
    },
    // handles on success
    onSuccess: (payment) => setClientSecret(payment.client_secret),
    // handles on error
    onError: (error) => {
      toast.error(toastErrorMessage(error, t('market.offer.holderSaveFailed')))
    },
  })

  // remembers which tickets were already held so the new one can be spotted
  const handlePaySuccess = () => {
    ticketsBeforePay.current = new Set((myTickets ?? []).map((tk) => tk.id))
    setConfirming(true)
  }

  const transferred = myTickets?.some((tk) => !ticketsBeforePay.current.has(tk.id)) ?? false

  useEffect(() => {
    if (!confirming) return

    // closes the wait and hands the buyer their ticket
    const finish = () => {
      toast.success(t('market.toast.paymentSuccess'))
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      void queryClient.invalidateQueries({ queryKey: ['market'] })
      void navigate({ to: '/tickets' })
    }

    if (transferred) {
      finish()
      return
    }
    const timer = setTimeout(finish, 20_000)
    return () => clearTimeout(timer)
  }, [confirming, transferred, navigate, queryClient, t])

  if (isLoading) {
    return (
      <div className="mx-auto max-w-[430px] space-y-4 px-4 pt-5 pb-28">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-56 w-full rounded-2xl" />
      </div>
    )
  }

  if (isError || !offer) {
    return <PageError onRetry={() => void refetch()} />
  }

  const documentValid = isValidDocument(documentNumber, documentType)
  const ready = holderName.trim().length > 0 && documentValid
  const expired = offer.state !== 'pending' || countdown === 0

  return (
    <div className="mx-auto max-w-[430px] px-4 pt-5 pb-28">
      <BackButton to="/market/offers/$offerId" params={{ offerId }} className="mb-6" />

      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">{t('market.offer.checkoutTitle')}</h1>
        {!expired && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 shrink-0 text-yellow-400" />
            <span
              className={cn(
                'font-mono text-sm font-semibold',
                countdown < 60 ? 'text-destructive' : 'text-yellow-400',
              )}
            >
              {formatSeconds(countdown)}
            </span>
          </div>
        )}
      </div>

      <div className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5">
        <div>
          <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">
            {event?.name ?? '—'}
          </p>
          <h2 className="text-lg leading-tight font-bold">
            {offer.ticket_type_name ?? t('market.offer.generalAdmission')}
          </h2>
        </div>

        <div className="border-t border-white/10" />

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{t('market.offer.price')}</span>
          <span className="text-primary text-lg font-bold">
            {formatPrice(offer.price_cents, offer.currency)}
          </span>
        </div>
      </div>

      {!clientSecret && !confirming && (
        <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-white/5 p-5">
          <div>
            <p className="text-sm font-semibold">{t('market.offer.holderTitle')}</p>
            <p className="text-muted-foreground mt-0.5 text-xs">
              {t('market.offer.holderDescription')}
            </p>
          </div>

          <input
            type="text"
            placeholder={t('market.offer.holderName')}
            value={holderName}
            onChange={(e) => setHolderName(e.target.value)}
            className="placeholder:text-muted-foreground w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-white/30 focus:outline-none"
          />

          <div className="flex gap-2">
            <div className="relative shrink-0">
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value as DocumentType)}
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
              placeholder={t(`tickets.holders.documentPlaceholder.${documentType}`)}
              value={documentNumber}
              onChange={(e) => setDocumentNumber(e.target.value)}
              className={cn(
                'placeholder:text-muted-foreground w-full rounded-xl border bg-white/5 px-4 py-2.5 text-sm text-white focus:outline-none',
                documentNumber && !documentValid
                  ? 'border-red-500/60 focus:border-red-500/80'
                  : 'border-white/10 focus:border-white/30',
              )}
            />
          </div>

          {documentNumber && !documentValid && (
            <p className="px-1 text-xs text-red-400">
              {t(`tickets.holders.invalid.${documentType}`)}
            </p>
          )}

          <div className="flex justify-end pt-1">
            <button
              onClick={() => pay.mutate()}
              disabled={!ready || expired || pay.isPending}
              className="bg-primary flex h-11 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white shadow-lg transition-opacity disabled:opacity-40"
            >
              <CreditCard className="h-4 w-4" />
              {t('market.offer.acceptAndPay')}
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
    </div>
  )
}
