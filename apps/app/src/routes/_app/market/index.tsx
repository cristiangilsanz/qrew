import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeftRight, Calendar, Clock, MapPin, Search, Ticket } from 'lucide-react'

import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useEvent } from '@/features/events/hooks/useEvent'
import { usePendingMarketAssignment } from '@/features/market/hooks/useMarketAssignment'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

function formatSeconds(s: number) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export const Route = createFileRoute('/_app/market/')({
  component: MarketPage,
})

function formatPrice(cents: number, currency: string) {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

function AssignmentSection() {
  const { data: assignment, isLoading } = usePendingMarketAssignment()
  const { data: event } = useEvent(assignment?.event_id ?? '')
  const countdown = useCountdown(assignment?.state === 'pending' ? assignment.expires_at : null)

  if (isLoading) {
    return (
      <section className="space-y-3">
        <Skeleton className="h-4 w-32" />
        <div className="bg-card border-border overflow-hidden rounded-xl border">
          <Skeleton className="h-44 w-full rounded-none" />
          <div className="space-y-2 p-4">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
      </section>
    )
  }

  if (!assignment) return null

  const expired = countdown === 0
  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? assignment.event_name ?? 'Event ticket'

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50">
        My Assignments
      </h2>

      <Link
        to="/market/assignments/$assignmentId"
        params={{ assignmentId: assignment.id }}
        className="block"
      >
        {/* EventCard-style layout */}
        <article className="bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors">
          {/* Image — same as EventCard h-44 */}
          <div className="relative h-44 w-full overflow-hidden bg-[#111]">
            <ImageWithSkeleton
              src={imageUrl}
              alt={eventName}
              className={cn('h-full w-full', event?.image_url ? 'object-cover' : 'object-contain p-4')}
            />
            {event?.image_url && (
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            )}

            {/* Resale badge */}
            <div className="absolute top-3 left-3">
              <StatusChip label="Resale" variant="reserved" />
            </div>

            {/* Countdown */}
            <div className={cn(
              'absolute top-3 right-3 flex items-center gap-1.5 rounded-full px-2.5 py-1 backdrop-blur-sm',
              expired ? 'bg-red-500/80' : 'bg-black/60',
            )}>
              <Clock className="h-3 w-3 text-white" />
              <span className="font-mono text-xs font-semibold text-white">
                {expired ? 'Expired' : formatSeconds(countdown)}
              </span>
            </div>
          </div>

          {/* Info — same padding and structure as EventCard */}
          <div className="space-y-2 p-4">
            <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {event?.organisation?.name ?? event?.organiser_name ?? 'Resale Market'}
            </p>
            <h2 className="text-base leading-snug font-semibold">{eventName}</h2>

            <div className="text-muted-foreground flex flex-wrap gap-3 text-xs">
              {event?.venue_city && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 shrink-0" />
                  {event.venue_city}
                </span>
              )}
              {event?.starts_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 shrink-0" />
                  {new Date(event.starts_at).toLocaleDateString('en-GB', {
                    weekday: 'short',
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
            </div>
          </div>
        </article>
      </Link>
    </section>
  )
}

function ListingsSection() {
  const { data: tickets, isLoading } = useTickets()
  const listedTickets = (tickets ?? []).filter((t) => t.state === 'frozen')

  if (isLoading) {
    return (
      <section className="space-y-3">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-16 w-full rounded-2xl" />
      </section>
    )
  }

  if (listedTickets.length === 0) return null

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50">My Listings</h2>
      <div className="space-y-2">
        {listedTickets.map((ticket) => (
          <Link
            key={ticket.id}
            to="/tickets/$ticketId"
            params={{ ticketId: ticket.id }}
            className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 transition hover:bg-white/8 active:scale-[0.98]"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/10">
              <Ticket className="h-5 w-5 text-white/60" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">
                {ticket.holder_name ?? 'Ticket'}
              </p>
              <p className="text-muted-foreground text-xs">Listed · Waiting for a buyer</p>
            </div>
            <StatusChip label="On sale" variant="frozen" />
          </Link>
        ))}
      </div>
    </section>
  )
}

function MarketPage() {
  const { data: pendingAssignment } = usePendingMarketAssignment()
  const { data: tickets } = useTickets()
  const listedTickets = (tickets ?? []).filter((t) => t.state === 'frozen')

  const isEmpty = !pendingAssignment && listedTickets.length === 0

  return (
    <div className="mx-auto min-h-screen max-w-[430px] px-4 pt-5 pb-28 space-y-6">
      <h1 className="text-2xl font-bold">Market</h1>

      <ListingsSection />
      <AssignmentSection />

      {isEmpty && (
        <div className="flex flex-col items-center justify-center gap-4 pt-20 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5">
            <ArrowLeftRight className="h-7 w-7 text-white/30" />
          </div>
          <div>
            <p className="font-semibold">Nothing here yet</p>
            <p className="text-muted-foreground mt-1 text-sm">
              Join the queue for a sold-out event,<br />or list a ticket you can&apos;t make.
            </p>
          </div>
          <Link
            to="/events"
            className="mt-2 flex items-center gap-2 rounded-full bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-400"
          >
            <Search className="h-4 w-4" />
            Browse events
          </Link>
        </div>
      )}
    </div>
  )
}
