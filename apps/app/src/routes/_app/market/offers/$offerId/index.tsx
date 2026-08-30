// implements assignment id
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import axios from 'axios'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  CreditCard,
  Loader2,
  TicketX,
  XCircle,
} from 'lucide-react'
import { Suspense, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { NotFound } from '@/components/ui/not-found'
import { PageError } from '@/components/ui/page-error'
import { Skeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketOffer } from '@/features/market/hooks/useMarketOffer'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { isNotFound } from '@/lib/errors'
import { lazyWithReload } from '@/lib/lazyWithReload'
// renders the stripe checkout component
const StripeCheckout = lazyWithReload(() =>
  import('@/features/tickets/components/StripeCheckout').then((m) => ({
    default: m.StripeCheckout,
  })),
)
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/offers/$offerId/')({
  component: AssignmentPage,
})

// implements format seconds
function formatSeconds(s: number): string {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

// implements format price
function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

// implements extract message
function extractMessage(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) return fallback
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message)
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as Record<string, unknown>
    return String(first.msg ?? first.message ?? fallback)
  }
  return fallback
}

// renders the assignment page component
function AssignmentPage() {
  const { t } = useTranslation()
  const { offerId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    data: assignment,
    isLoading: assignmentLoading,
    isError,
    error,
    refetch,
  } = useMarketOffer(offerId)
  const { data: event, isLoading: eventLoading } = useEvent(assignment?.event_id ?? '')
  const countdown = useCountdown(assignment?.state === 'pending' ? assignment.expires_at : null)

  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const ticketIdsBeforePay = useRef<Set<string>>(new Set())
  const { data: myTickets } = useTickets(confirming)
  const [declineOpen, setDeclineOpen] = useState(false)
  const [declineSeconds, setDeclineSeconds] = useState(5)
  const declineTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!declineOpen) {
      setDeclineSeconds(5)
      return
    }
    declineTimerRef.current = setInterval(() => {
      setDeclineSeconds((s) => {
        if (s <= 1) {
          clearInterval(declineTimerRef.current!)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => {
      if (declineTimerRef.current) clearInterval(declineTimerRef.current)
    }
  }, [declineOpen])

  const initiatePayment = useMutation({
    // implements mutation fn
    mutationFn: () => marketApi.initiateOfferPayment(offerId),
    // handles on success
    onSuccess: (payment) => setClientSecret(payment.client_secret),
    // handles on error
    onError: (err) => {
      toast.error(extractMessage(err, t('market.toast.declineFailed')))
    },
  })

  const declineOffer = useMutation({
    // implements mutation fn
    mutationFn: () => marketApi.declineOffer(offerId),
    // handles on success
    onSuccess: () => {
      toast.success(t('market.toast.declined'))
      void queryClient.invalidateQueries({ queryKey: ['market'] })
      void navigate({ to: '/market' })
    },
    // handles on error
    onError: () => toast.error(t('market.toast.declineFailed')),
  })

  // handles handle pay success
  const handlePaySuccess = () => {
    ticketIdsBeforePay.current = new Set((myTickets ?? []).map((tk) => tk.id))
    setConfirming(true)
  }

  const ticketTransferred = myTickets?.some((tk) => !ticketIdsBeforePay.current.has(tk.id)) ?? false

  useEffect(() => {
    if (!confirming) return

    // closes the wait and hands the user their ticket
    const finish = () => {
      toast.success(t('market.toast.paymentSuccess'))
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      void queryClient.invalidateQueries({ queryKey: ['market'] })
      void navigate({ to: '/tickets' })
    }

    if (ticketTransferred) {
      finish()
      return
    }
    const timer = setTimeout(finish, 20_000)
    return () => clearTimeout(timer)
  }, [confirming, ticketTransferred, navigate, queryClient, t])

  const isLoading = assignmentLoading || (!!assignment && eventLoading)

  if (isLoading) {
    return (
      <div className="pb-32">
        <Skeleton className="h-64 w-full rounded-none" />
        <div className="mx-auto max-w-[430px] space-y-4 px-4 pt-4">
          <div className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-7 w-3/4" />
            <Skeleton className="h-12 w-full" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-12 w-full rounded-xl" />
          <div className="space-y-1.5 rounded-xl border border-white/10 p-4">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
      </div>
    )
  }

  if (isError && !isNotFound(error)) {
    return <PageError onRetry={() => void refetch()} />
  }

  if (isError || !assignment) {
    return <NotFound message={t('common.resourceGone')} />
  }

  const isPaid = assignment.state === 'paid'
  const isExpired = assignment.state === 'expired'
  const isDeclined = assignment.state === 'declined'
  const countdownExpired = countdown === 0 && assignment.state === 'pending'
  const isPending = assignment.state === 'pending' && !countdownExpired
  const accepting = initiatePayment.isPending

  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? assignment.event_name ?? t('market.resaleMarket')
  const startDate = event?.starts_at ? new Date(event.starts_at) : null

  return (
    <div className="flex flex-col pb-24">
      <div className="relative h-64 overflow-hidden bg-[#111]">
        <ImageWithSkeleton
          src={imageUrl}
          alt={eventName}
          className={cn(
            'absolute inset-0 h-full w-full',
            event?.image_url ? 'object-cover opacity-80' : 'object-contain p-8 opacity-60',
          )}
        />
        {event?.image_url && (
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-transparent" />
        )}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent" />

        <BackButton to="/market" className="absolute top-4 left-4" />
      </div>

      <div className="mx-auto w-full max-w-[430px] space-y-5 px-4 py-4">
        <div>
          <div className="mb-1 flex items-center justify-between">
            <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {event?.organisation?.name ?? event?.organiser_name ?? t('market.resaleMarket')}
            </p>
            {assignment.state === 'pending' && countdown > 0 && (
              <div
                className={cn(
                  'flex shrink-0 items-center gap-1',
                  countdown < 60 ? 'text-red-400' : 'text-yellow-400',
                )}
              >
                <Clock className="h-3 w-3" />
                <span className="font-mono text-xs font-semibold">{formatSeconds(countdown)}</span>
              </div>
            )}
          </div>
          <h1 className="text-2xl font-bold">{eventName}</h1>
        </div>

        {event?.description && (
          <p className="text-muted-foreground text-sm leading-relaxed">{event.description}</p>
        )}

        {startDate && (
          <div className="text-muted-foreground text-sm">
            <span className="flex items-center gap-2">
              <Calendar className="h-4 w-4 shrink-0" />
              {startDate.toLocaleDateString('en-GB', {
                weekday: 'short',
                day: 'numeric',
                month: 'long',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        )}

        {assignment.event_id && (
          <Link
            to="/events/$eventId"
            params={{ eventId: assignment.event_id }}
            className="flex items-center justify-between rounded-xl border border-white/10 px-4 py-3 transition-colors hover:bg-white/5"
          >
            <span className="text-sm font-medium">{t('market.offer.viewEventDetails')}</span>
            <ChevronRight className="h-4 w-4 text-white/40" />
          </Link>
        )}

        {(() => {
          // implements ticket type
          const ticketType = event?.ticket_types?.find(
            (tt) => tt.id === assignment.ticket_type_id || tt.name === assignment.ticket_type_name,
          )
          return (
            <div className="rounded-xl border border-white/10 p-4">
              <p className="leading-tight font-semibold">
                {assignment.ticket_type_name ??
                  ticketType?.name ??
                  t('market.offer.generalAdmission')}
              </p>
              {ticketType?.description && (
                <p className="text-muted-foreground mt-0.5 text-xs">{ticketType.description}</p>
              )}
              <p className="text-primary mt-1 text-sm font-bold">
                {formatPrice(assignment.price_cents, assignment.currency)}
              </p>
            </div>
          )
        })()}
      </div>

      {clientSecret && !confirming && (
        <div className="mx-auto mt-5 w-full max-w-[430px] px-4 pb-32">
          <Suspense fallback={null}>
            <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaySuccess} />
          </Suspense>
        </div>
      )}

      {confirming && (
        <div className="mx-auto mt-5 flex w-full max-w-[430px] flex-col items-center gap-3 px-4 py-10 text-center">
          <Loader2 className="text-primary h-8 w-8 animate-spin" />
          <p className="text-muted-foreground text-sm">{t('tickets.payment.confirming')}</p>
        </div>
      )}

      {isPaid && (
        <div className="mx-auto mt-5 w-full max-w-[430px] px-4">
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-green-400/20 bg-green-400/5 p-6 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
            <p className="text-sm font-semibold text-green-400">
              {t('market.offer.paymentConfirmed')}
            </p>
            <p className="text-muted-foreground text-xs">{t('market.offer.ticketTransferring')}</p>
          </div>
        </div>
      )}
      {(isExpired || countdownExpired) && (
        <div className="mx-auto mt-2 flex w-full max-w-[430px] flex-col items-center space-y-2 px-4">
          <TicketX className="h-7 w-7 text-white/20" />
          <p className="text-muted-foreground text-center text-base font-semibold">
            {t('market.offer.expired')}
          </p>
        </div>
      )}
      {isDeclined && (
        <div className="mx-auto mt-2 flex w-full max-w-[430px] flex-col items-center space-y-2 px-4">
          <TicketX className="h-7 w-7 text-white/20" />
          <p className="text-muted-foreground text-center text-base font-semibold">
            {t('market.offer.declined')}
          </p>
        </div>
      )}

      {isPending && !clientSecret && (
        <div className="keyboard-hide fixed inset-x-0 bottom-24 z-40">
          <div className="mx-auto w-full max-w-[430px] space-y-3 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent px-4 pt-8">
            <div className="flex items-center justify-between border-t border-white/10 pt-3 pb-1">
              <span className="text-muted-foreground text-sm">{t('market.offer.total')}</span>
              <span className="text-lg font-bold">
                {formatPrice(assignment.price_cents, assignment.currency)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <button
                onClick={() => setDeclineOpen(true)}
                className="flex h-14 items-center gap-2 rounded-full bg-red-500 pr-6 pl-5 text-sm font-semibold text-white shadow-lg transition-colors hover:bg-red-600"
              >
                <XCircle className="h-4 w-4 shrink-0" />
                {t('market.offer.decline')}
              </button>
              <button
                onClick={() => initiatePayment.mutate()}
                disabled={accepting || countdownExpired}
                className="bg-primary hover:bg-primary/90 flex h-14 shrink-0 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white shadow-lg transition disabled:opacity-40"
              >
                <CreditCard className="h-4 w-4" />
                {t('market.offer.acceptAndPay')}
              </button>
            </div>
          </div>
        </div>
      )}

      <AnimatePresence>
        {declineOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[200] flex items-center justify-center p-4"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setDeclineOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <XCircle className="h-5 w-5 text-red-400" />
                </div>
                <h3 className="text-base font-semibold text-red-400">
                  {t('market.offer.declineTitle')}
                </h3>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">{t('market.offer.declineDesc')}</p>
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setDeclineOpen(false)}
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => {
                    setDeclineOpen(false)
                    declineOffer.mutate()
                  }}
                  disabled={declineSeconds > 0 || declineOffer.isPending}
                  className="flex h-10 min-w-[112px] items-center justify-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {declineSeconds > 0 ? (
                    t('common.waitSeconds', { seconds: declineSeconds })
                  ) : (
                    <>
                      <XCircle className="h-3.5 w-3.5" />
                      {t('market.offer.decline')}
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
