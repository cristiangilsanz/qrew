import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Link } from '@tanstack/react-router'
import axios from 'axios'
import { AnimatePresence, motion } from 'framer-motion'
import { Calendar, CheckCircle2, ChevronRight, Clock, CreditCard, ShieldX, XCircle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { Skeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketAssignment } from '@/features/market/hooks/useMarketAssignment'
import { StripeCheckout } from '@/features/tickets/components/StripeCheckout'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/assignments/$assignmentId/')({
  component: AssignmentPage,
})

function formatSeconds(s: number): string {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

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


function AssignmentPage() {
  const { t } = useTranslation()
  const { assignmentId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: assignment, isLoading: assignmentLoading, isError } = useMarketAssignment(assignmentId)
  const { data: event, isLoading: eventLoading } = useEvent(assignment?.event_id ?? '')
  const countdown = useCountdown(assignment?.state === 'pending' ? assignment.expires_at : null)

  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [declineOpen, setDeclineOpen] = useState(false)
  const [declineSeconds, setDeclineSeconds] = useState(5)
  const declineTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!declineOpen) { setDeclineSeconds(5); return }
    declineTimerRef.current = setInterval(() => {
      setDeclineSeconds((s) => {
        if (s <= 1) { clearInterval(declineTimerRef.current!); return 0 }
        return s - 1
      })
    }, 1000)
    return () => { if (declineTimerRef.current) clearInterval(declineTimerRef.current) }
  }, [declineOpen])

  const initiatePayment = useMutation({
    mutationFn: () => marketApi.initiateAssignmentPayment(assignmentId),
    onSuccess: (payment) => setClientSecret(payment.client_secret),
    onError: (err) => {
      toast.error(extractMessage(err, t('market.toast.declineFailed')))
    },
  })

  const declineAssignment = useMutation({
    mutationFn: () => marketApi.declineAssignment(assignmentId),
    onSuccess: () => {
      toast.success(t('market.toast.declined'))
      void queryClient.invalidateQueries({ queryKey: ['market'] })
      void navigate({ to: '/market' })
    },
    onError: () => toast.error(t('market.toast.declineFailed')),
  })

  const handlePaySuccess = () => {
    toast.success(t('market.toast.paymentSuccess'))
    void queryClient.invalidateQueries({ queryKey: ['tickets'] })
    void queryClient.invalidateQueries({ queryKey: ['market'] })
    void navigate({ to: '/tickets' })
  }

  const isLoading = assignmentLoading || (!!assignment && eventLoading)

  if (isLoading) {
    return (
      <div className="min-h-screen pb-32">
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
          <div className="rounded-xl border border-white/10 p-4 space-y-1.5">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
      </div>
    )
  }

  if (isError || !assignment) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <ShieldX className="h-10 w-10 text-white/30" />
        <p className="text-muted-foreground text-sm">{t('market.assignment.notFound')}</p>
      </div>
    )
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
    <div className="min-h-screen flex flex-col pb-24">
      {/* Hero image */}
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

      {/* Event info */}
      <div className="mx-auto w-full max-w-[430px] space-y-5 px-4 py-4">
        {/* Org + timer + title */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {event?.organisation?.name ?? event?.organiser_name ?? t('market.resaleMarket')}
            </p>
            {assignment.state === 'pending' && countdown > 0 && (
              <div className={cn('flex shrink-0 items-center gap-1', countdown < 60 ? 'text-red-400' : 'text-yellow-400')}>
                <Clock className="h-3 w-3" />
                <span className="font-mono text-xs font-semibold">{formatSeconds(countdown)}</span>
              </div>
            )}
          </div>
          <h1 className="text-2xl font-bold">{eventName}</h1>
        </div>

        {/* Description */}
        {event?.description && (
          <p className="text-muted-foreground text-sm leading-relaxed">{event.description}</p>
        )}

        {/* Date */}
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

        {/* Link to event detail */}
        {assignment.event_id && (
          <Link
            to="/events/$eventId"
            params={{ eventId: assignment.event_id }}
            className="flex items-center justify-between rounded-xl border border-white/10 px-4 py-3 transition-colors hover:bg-white/5"
          >
            <span className="text-sm font-medium">{t('market.assignment.viewEventDetails')}</span>
            <ChevronRight className="h-4 w-4 text-white/40" />
          </Link>
        )}

        {/* Ticket type card */}
        {(() => {
          const ticketType = event?.ticket_types?.find(
            (tt) => tt.id === assignment.ticket_type_id || tt.name === assignment.ticket_type_name,
          )
          return (
            <div className="rounded-xl border border-white/10 p-4">
              <p className="font-semibold leading-tight">
                {assignment.ticket_type_name ?? ticketType?.name ?? t('market.assignment.generalAdmission')}
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

      {/* Stripe checkout */}
      {clientSecret && (
        <div className="mx-auto mt-5 max-w-[430px] px-4 pb-32">
          <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaySuccess} />
        </div>
      )}

      {/* Terminal states */}
      {isPaid && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-green-400/20 bg-green-400/5 p-6 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
            <p className="text-sm font-semibold text-green-400">{t('market.assignment.paymentConfirmed')}</p>
            <p className="text-muted-foreground text-xs">{t('market.assignment.ticketTransferring')}</p>
          </div>
        </div>
      )}
      {(isExpired || countdownExpired) && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-sm font-semibold text-white/60">{t('market.assignment.expired')}</p>
            <p className="text-muted-foreground mt-1 text-xs">{t('market.assignment.expiredDesc')}</p>
          </div>
        </div>
      )}
      {isDeclined && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-muted-foreground text-sm">{t('market.assignment.declined')}</p>
          </div>
        </div>
      )}

      {/* Bottom: total + action buttons */}
      {isPending && !clientSecret && (
        <div className="fixed inset-x-0 bottom-24 z-40">
          <div className="mx-auto w-full max-w-[430px] space-y-3 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent px-4 pt-8 pb-0">
            <div className="flex items-center justify-between border-t border-white/10 pt-3 pb-1">
              <span className="text-muted-foreground text-sm">{t('market.assignment.total')}</span>
              <span className="text-lg font-bold">
                {formatPrice(assignment.price_cents, assignment.currency)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <button
                onClick={() => setDeclineOpen(true)}
                className="flex h-14 items-center gap-2 rounded-full bg-red-500 pl-5 pr-6 text-sm font-semibold text-white shadow-lg transition-colors hover:bg-red-600"
              >
                <XCircle className="h-4 w-4 shrink-0" />
                {t('market.assignment.decline')}
              </button>
              <button
                onClick={() => initiatePayment.mutate()}
                disabled={accepting || countdownExpired}
                className="bg-primary hover:bg-primary/90 flex h-14 shrink-0 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white shadow-lg transition disabled:opacity-40"
              >
                {accepting ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <CreditCard className="h-4 w-4" />
                )}
                {t('market.assignment.acceptAndPay')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decline confirmation modal */}
      <AnimatePresence>
        {declineOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setDeclineOpen(false)}
          >
            <motion.div
              initial={{ y: 32, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 32, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <XCircle className="h-5 w-5 text-red-400" />
                </div>
                <h3 className="text-base font-semibold text-red-400">{t('market.assignment.declineTitle')}</h3>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">
                {t('market.assignment.declineDesc')}
              </p>
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setDeclineOpen(false)}
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => { setDeclineOpen(false); declineAssignment.mutate() }}
                  disabled={declineSeconds > 0 || declineAssignment.isPending}
                  className="flex h-10 min-w-[112px] items-center justify-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {declineAssignment.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : declineSeconds > 0 ? (
                    t('common.waitSeconds', { seconds: declineSeconds })
                  ) : (
                    <>
                      <XCircle className="h-3.5 w-3.5" />
                      {t('market.assignment.decline')}
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
