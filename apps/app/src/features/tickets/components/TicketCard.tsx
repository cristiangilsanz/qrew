import { Link } from '@tanstack/react-router'
import { Calendar, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useEvent } from '@/features/events/hooks/useEvent'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

import type { Ticket, TicketState } from '../api'
import { useReservation } from '../hooks/useReservation'


interface Props {
  ticket: Ticket
}

export function TicketCard({ ticket }: Props) {
  const { t } = useTranslation()
  const { data: event } = useEvent(ticket.event_id)
  const { data: reservation, isLoading: reservationLoading } = useReservation(
    ticket.state === 'reserved' ? ticket.reservation_id : '',
  )
  const imageUrl = getEventImageUrl(event?.image_url)

  const badgeReady = ticket.state !== 'reserved' || !reservationLoading
  const displayState: TicketState =
    ticket.state === 'reserved' &&
    reservation &&
    (reservation.status === 'expired' || new Date(reservation.expires_at) < new Date())
      ? 'expired'
      : ticket.state

  return (
    <Link to="/tickets/$ticketId" params={{ ticketId: ticket.id }}>
      <article
        className={cn(
          'bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors',
        )}
      >
        {/* Image */}
        <div className="relative h-44 w-full overflow-hidden bg-[#111]">
          {!event ? (
            <Skeleton className="h-full w-full rounded-none" />
          ) : (
            <ImageWithSkeleton
              src={imageUrl}
              alt={event?.name}
              className={cn(
                'h-full w-full',
                event.image_url ? 'object-cover' : 'object-contain p-4',
              )}
            />
          )}
          {event?.image_url && (
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          )}
        </div>

        {/* Text section */}
        <div className="space-y-1.5 p-4">
          {!event ? (
            <>
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-5 w-3/4" />
              <div className="flex gap-3 pt-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-3 w-28" />
              </div>
            </>
          ) : (
            <>
              <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                {event.organisation?.name ?? 'Qrew'}
              </p>
              <h2 className="text-base leading-snug font-semibold">{event.name}</h2>
              <div className="text-muted-foreground flex flex-wrap gap-3 text-xs">
                {event.venue?.city && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5 shrink-0" />
                    {event.venue.city}
                  </span>
                )}
                {event.starts_at && (
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
                <span className="ml-auto flex items-center gap-2">
                  {badgeReady && (
                    <StatusChip
                      label={t(`tickets.ticket.states.${displayState}`)}
                      variant={displayState}
                    />
                  )}
                  <span className="font-mono text-xs">
                    #{ticket.id.slice(0, 8).toUpperCase()}
                  </span>
                </span>
              </div>
            </>
          )}
        </div>
      </article>
    </Link>
  )
}
