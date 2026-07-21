import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Calendar, MapPin, Ticket, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { EventDetailSkeleton, Skeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { QueuePanel } from '@/features/tickets/components/QueuePanel'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/events/$eventId/')({
  component: EventDetailPage,
})

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

function useCountdown(targetIso: string | null): number {
  const [secondsLeft, setSecondsLeft] = useState(0)
  useEffect(() => {
    if (!targetIso) return
    const update = () => {
      setSecondsLeft(Math.max(0, Math.floor((new Date(targetIso).getTime() - Date.now()) / 1000)))
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [targetIso])
  return secondsLeft
}

function formatCountdown(s: number): string {
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (d > 0)
    return `${d}d ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function EventDetailPage() {
  const { t } = useTranslation()
  const { eventId } = Route.useParams()
  const navigate = useNavigate()
  const { data: event, isLoading, isError } = useEvent(eventId)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [showQueue, setShowQueue] = useState(false)

  const now = new Date()
  const saleStarts = event ? new Date(event.sale_starts_at) : null
  const saleEnds = event ? new Date(event.sale_ends_at) : null
  const saleNotStarted = saleStarts ? now < saleStarts : false
  const secondsUntilSale = useCountdown(saleNotStarted && event ? event.sale_starts_at : null)

  if (isLoading) return <EventDetailSkeleton />

  if (showQueue && event) {
    return (
      <QueueWaitingRoom
        eventId={eventId}
        eventName={event.name}
        onBack={() => setShowQueue(false)}
      />
    )
  }

  if (isError || !event) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">{t('events.notFound')}</p>
      </div>
    )
  }

  const imageUrl = getEventImageUrl(event.image_url)
  const allSoldOut = event.ticket_types.every((tt) => tt.available === 0)
  const saleEnded = saleEnds ? now > saleEnds : false
  const mapsUrl = `https://maps.google.com/maps?q=${event.venue.latitude},${event.venue.longitude}&t=&z=15&ie=UTF8&iwloc=&output=embed`

  return (
    <div className="pb-24">
      {/* Hero */}
      <div className="relative h-64 overflow-hidden bg-[#111]">
        <ImageWithSkeleton
          src={imageUrl}
          alt={event.name}
          className={cn(
            'absolute inset-0 h-full w-full',
            event.image_url ? 'object-cover opacity-80' : 'object-contain p-8 opacity-60',
          )}
        />
        {/* top gradient overlay */}
        {event.image_url && (
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-transparent" />
        )}
        {/* bottom fade to background */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent" />

        {/* Back button */}
        <BackButton
          onClick={() => void navigate({ to: '/events' })}
          className="absolute top-4 left-4"
        />
      </div>

      {/* Content */}
      <div className="space-y-5 px-4 py-4">
        <div>
          <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">
            {event.organisation.name}
          </p>
          <h1 className="text-2xl font-bold">{event.name}</h1>
        </div>

        {/* Description */}
        {event.description && (
          <p className="text-muted-foreground text-sm leading-relaxed">{event.description}</p>
        )}

        {/* Start date */}
        <div className="text-muted-foreground text-sm">
          <span className="flex items-center gap-2">
            <Calendar className="h-4 w-4 shrink-0" />
            {formatDate(event.starts_at)}
          </span>
        </div>

        {/* Location */}
        <div className="space-y-2">
          <h2 className="text-base font-semibold">Location</h2>
          <span className="text-muted-foreground flex items-center gap-2 text-sm">
            <MapPin className="h-4 w-4 shrink-0" />
            {event.venue.name}, {event.venue.city}, {event.venue.country}
          </span>
          <div className="relative mt-2 h-48 w-full overflow-hidden rounded-xl">
            {!mapLoaded && <Skeleton className="absolute inset-0 rounded-xl" />}
            <iframe
              src={mapsUrl}
              className="h-full w-full border-0"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              title="Event location map"
              onLoad={() => setMapLoaded(true)}
            />
          </div>
        </div>
      </div>

      {/* Sticky FAB — bottom right, above dock */}
      {saleNotStarted ? (
        <div className="fixed inset-x-0 bottom-24 z-40 flex justify-center">
          <div className="mx-auto w-full max-w-[430px] px-4 text-center">
            <p className="text-muted-foreground mb-0.5 text-xs">Tickets on sale in</p>
            <p className="font-mono text-2xl font-bold text-white tabular-nums">
              {formatCountdown(secondsUntilSale)}
            </p>
          </div>
        </div>
      ) : saleEnded ? (
        <button
          disabled
          className="fixed bottom-24 z-40 flex h-14 items-center gap-2 rounded-full bg-white/20 px-5 text-white/50 shadow-lg"
          style={{ right: 'max(calc((100vw - 430px) / 2 + 1rem), 1rem)' }}
        >
          <Ticket className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">Sales ended</span>
        </button>
      ) : allSoldOut ? (
        <button
          disabled
          className="fixed bottom-24 z-40 flex h-14 items-center gap-2 rounded-full bg-white/20 px-5 text-white/50 shadow-lg"
          style={{ right: 'max(calc((100vw - 430px) / 2 + 1rem), 1rem)' }}
        >
          <Ticket className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">{t('events.soldOut')}</span>
        </button>
      ) : event.queue_required ? (
        <button
          onClick={() => setShowQueue(true)}
          className="bg-primary hover:bg-primary/90 fixed bottom-24 z-40 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
          style={{ right: 'max(calc((100vw - 430px) / 2 + 1rem), 1rem)' }}
        >
          <Users className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">{t('tickets.queue.joinButton')}</span>
        </button>
      ) : (
        <button
          onClick={() => void navigate({ to: '/events/$eventId/checkout', params: { eventId } })}
          className="bg-primary hover:bg-primary/90 fixed bottom-24 z-40 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
          style={{ right: 'max(calc((100vw - 430px) / 2 + 1rem), 1rem)' }}
        >
          <Ticket className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">{t('tickets.checkout.buyButton')}</span>
        </button>
      )}
    </div>
  )
}

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
