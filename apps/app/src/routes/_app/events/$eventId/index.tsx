// implements event id
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Calendar, LogOut, MapPin, Shuffle, Ticket, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { FloatingActions } from '@/components/ui/floating-actions'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { NotFound } from '@/components/ui/not-found'
import { PageError } from '@/components/ui/page-error'
import { EventDetailSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketQueueStatus } from '@/features/market/hooks/useMarketQueueStatus'
import { QueuePanel } from '@/features/tickets/components/QueuePanel'
import { useQueuePosition } from '@/features/tickets/hooks/useQueuePosition'
import { isNotFound } from '@/lib/errors'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/events/$eventId/')({
  component: EventDetailPage,
})

// implements format date
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// implements format compact
function formatCompact(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
  })
}

// provides use countdown
function useCountdown(targetIso: string | null): number {
  const [secondsLeft, setSecondsLeft] = useState(0)
  useEffect(() => {
    if (!targetIso) return
    // implements update
    const update = () => {
      setSecondsLeft(Math.max(0, Math.floor((new Date(targetIso).getTime() - Date.now()) / 1000)))
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [targetIso])
  return secondsLeft
}

// implements format countdown
function formatCountdown(s: number): string {
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (d > 0)
    return `${d}d ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

// renders the event detail page component
function EventDetailPage() {
  const { t } = useTranslation()
  const { eventId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: event, isLoading, isError, error, refetch } = useEvent(eventId)
  const [showQueue, setShowQueue] = useState(false)
  const [leaveOpen, setLeaveOpen] = useState(false)

  const saleNotStarted = event?.availability_status === 'not_started'
  const secondsUntilSale = useCountdown(saleNotStarted && event ? event.sale_starts_at : null)

  // the resale queue opens on the same rule the backend applies, which is that the event
  // can no longer be bought from, by date or because every tier ran out
  const saleEnded =
    event?.availability_status === 'ended' || event?.availability_status === 'sold_out'
  const isPublished = event?.status === 'published'
  const showResaleQueue = isPublished && saleEnded
  const saleOpen = isPublished && event?.availability_status === 'open'
  const eventFinished = event ? new Date(event.ends_at).getTime() <= Date.now() : false
  const eventCancelled = event?.status === 'cancelled'

  const { data: purchaseQueue } = useQueuePosition(
    eventId,
    event?.queue_required === true && event.availability_status === 'open',
  )
  const queuePosition = purchaseQueue?.position ?? null
  const queueAdmitted = queuePosition === null && !!purchaseQueue?.redeem_token

  const { data: queueStatus, isLoading: queueLoading } = useMarketQueueStatus(
    eventId,
    showResaleQueue,
  )

  const joinQueue = useMutation({
    // implements mutation fn
    mutationFn: () => marketApi.joinQueue(eventId),
    // handles on success
    onSuccess: () => {
      toast.success(t('market.toast.joinSuccess'))
      void queryClient.invalidateQueries({ queryKey: ['market', 'queue', eventId] })
    },
    // handles on error
    onError: () => toast.error(t('market.toast.joinFailed')),
  })

  const leaveQueue = useMutation({
    // implements mutation fn
    mutationFn: () => marketApi.leaveQueue(eventId),
    // handles on success
    onSuccess: () => {
      toast.success(t('market.toast.leftWaitlist'))
      setLeaveOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['market', 'queue', eventId] })
      void queryClient.invalidateQueries({ queryKey: ['market', 'queues'] })
    },
    // handles on error
    onError: () => toast.error(t('market.toast.leaveFailed')),
  })

  if (isLoading || (showResaleQueue && queueLoading)) return <EventDetailSkeleton />

  if (showQueue && event) {
    return (
      <QueueWaitingRoom
        eventId={eventId}
        eventName={event.name}
        onBack={() => setShowQueue(false)}
      />
    )
  }

  if (isError && !isNotFound(error)) {
    return <PageError onRetry={() => void refetch()} />
  }

  if (isError || !event) {
    return <NotFound message={t('common.resourceGone')} />
  }

  const imageUrl = getEventImageUrl(event.image_url)
  const mapsUrl = `https://maps.google.com/maps?q=${event.venue.latitude},${event.venue.longitude}&t=&z=15&ie=UTF8&iwloc=&output=embed`
  const inQueue = queueStatus?.in_queue ?? false

  return (
    <div className="pb-24">
      <div className="relative h-64 overflow-hidden bg-[#111]">
        <ImageWithSkeleton
          src={imageUrl}
          alt={event.name}
          className={cn(
            'absolute inset-0 h-full w-full',
            event.image_url ? 'object-cover opacity-80' : 'object-contain p-8 opacity-60',
          )}
        />
        {event.image_url && (
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-transparent" />
        )}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent" />

        <BackButton to="/events" className="absolute top-4 left-4" />
      </div>

      <div className="space-y-5 px-4 py-4">
        <div>
          <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">
            {event.organisation.name}
          </p>
          <h1 className="text-2xl font-bold">{event.name}</h1>
        </div>

        {event.description && (
          <p className="text-muted-foreground text-sm leading-relaxed">{event.description}</p>
        )}

        <div className="text-muted-foreground flex items-center justify-between gap-3 text-sm">
          <span className="flex items-center gap-2">
            <Calendar className="h-4 w-4 shrink-0" />
            {formatDate(event.starts_at)}
          </span>
          {!eventFinished && !eventCancelled && (
            <span className="flex shrink-0 items-center gap-1.5 text-xs">
              <Ticket className="h-3.5 w-3.5 shrink-0" />
              {`${formatCompact(event.sale_starts_at)} - ${formatCompact(event.sale_ends_at)}`}
            </span>
          )}
        </div>

        <div className="space-y-2">
          <h2 className="text-base font-semibold">Location</h2>
          <span className="text-muted-foreground flex items-center gap-2 text-sm">
            <MapPin className="h-4 w-4 shrink-0" />
            {event.venue.name}, {event.venue.city}, {event.venue.country}
          </span>
          <div className="mt-2 h-48 w-full overflow-hidden rounded-xl bg-white/5">
            <iframe
              src={mapsUrl}
              className="h-full w-full border-0"
              loading="eager"
              referrerPolicy="no-referrer-when-downgrade"
              title="Event location map"
            />
          </div>
        </div>

        {saleNotStarted && (
          <div className="text-center">
            <p className="text-muted-foreground mb-0.5 text-xs">Tickets on sale in</p>
            <p className="font-mono text-2xl font-bold text-white tabular-nums">
              {formatCountdown(secondsUntilSale)}
            </p>
          </div>
        )}

        {showResaleQueue && (
          <div className="mt-8 flex flex-col items-center space-y-2">
            <Ticket className="h-7 w-7 text-white/20" />
            <p className="text-muted-foreground text-center text-base font-semibold">
              {t('events.soldOut')}
            </p>
          </div>
        )}

        {(eventFinished || eventCancelled) && (
          <div className="mt-8 flex flex-col items-center space-y-2">
            <Ticket className="h-7 w-7 text-white/20" />
            <p className="text-muted-foreground text-center text-base font-semibold">
              {eventCancelled ? t('events.cancelled') : t('events.finished')}
            </p>
          </div>
        )}
      </div>

      <FloatingActions>
        {showResaleQueue ? (
          inQueue ? (
            <button
              onClick={() => setLeaveOpen(true)}
              className="flex h-14 items-center gap-2 rounded-full bg-red-600 px-5 text-white shadow-lg transition-colors hover:bg-red-700"
            >
              <LogOut className="h-5 w-5 shrink-0" />
              <span className="text-sm font-semibold">{t('market.leaveWaitlistButton')}</span>
            </button>
          ) : (
            <button
              onClick={() => joinQueue.mutate()}
              disabled={joinQueue.isPending}
              className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors disabled:opacity-60"
            >
              <Shuffle className="h-5 w-5 shrink-0" />
              <span className="text-sm font-semibold">{t('market.joinWaitlistButton')}</span>
            </button>
          )
        ) : saleOpen ? (
          event.queue_required ? (
            <button
              onClick={() => setShowQueue(true)}
              className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
            >
              <Users className="h-5 w-5 shrink-0" />
              <span className="text-sm font-semibold">
                {queueAdmitted
                  ? t('tickets.queue.admittedButton')
                  : queuePosition !== null
                    ? t('tickets.queue.resumeButton')
                    : t('tickets.queue.joinButton')}
              </span>
            </button>
          ) : (
            <button
              onClick={() =>
                void navigate({ to: '/events/$eventId/checkout', params: { eventId } })
              }
              className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
            >
              <Ticket className="h-5 w-5 shrink-0" />
              <span className="text-sm font-semibold">{t('tickets.checkout.buyButton')}</span>
            </button>
          )
        ) : null}
      </FloatingActions>

      <ConfirmDialog
        open={leaveOpen}
        onOpenChange={setLeaveOpen}
        tone="destructive"
        icon={LogOut}
        title={t('market.leaveWaitlist.title')}
        description={t('market.leaveWaitlist.description')}
        irreversible
        confirmLabel={t('market.leaveWaitlist.confirm')}
        isLoading={leaveQueue.isPending}
        onConfirm={() => leaveQueue.mutate()}
      />
    </div>
  )
}

// renders the queue waiting room component
function QueueWaitingRoom({
  eventId,
  eventName,
  onBack,
}: {
  eventId: string
  eventName: string
  onBack: () => void
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen flex-col px-6 pt-12">
      <BackButton onClick={onBack} className="mb-6 self-start" />
      <h1 className="pt-2 text-2xl font-bold text-white">{eventName}</h1>

      <div className="mt-8 rounded-2xl border border-white/8 bg-white/[0.03] p-6">
        <p className="mb-6 text-base font-semibold text-white">{t('tickets.queue.title')}</p>
        <QueuePanel
          eventId={eventId}
          onAdmitted={(reservationWindowToken) =>
            void navigate({
              to: '/events/$eventId/checkout',
              params: { eventId },
              search: {
                admitted: true,
                ...(reservationWindowToken
                  ? { reservation_window_token: reservationWindowToken }
                  : {}),
              },
            })
          }
        />
      </div>
    </div>
  )
}
