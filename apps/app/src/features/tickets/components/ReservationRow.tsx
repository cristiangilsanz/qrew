import { Link, useNavigate } from '@tanstack/react-router'
import { Calendar, Clock, CreditCard, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useEvent } from '@/features/events/hooks/useEvent'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { useReservation } from '@/features/tickets/hooks/useReservation'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

import type { Ticket, TicketState } from '../api'

function formatSeconds(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}


interface StubProps {
  ticket: Ticket
  index: number
  total: number
  imageUrl: string
  hasRealImage: boolean
}

function TicketStub({ ticket, index, total, imageUrl, hasRealImage }: StubProps) {
  const { t } = useTranslation()
  const { data: reservation, isLoading: resLoading } = useReservation(
    ticket.state === 'reserved' ? ticket.reservation_id : '',
  )

  const badgeReady = ticket.state !== 'reserved' || !resLoading
  const displayState: TicketState =
    ticket.state === 'reserved' &&
    reservation &&
    (reservation.status === 'expired' || new Date(reservation.expires_at) < new Date())
      ? 'expired'
      : ticket.state

  return (
    <Link to="/tickets/$ticketId" params={{ ticketId: ticket.id }} className="shrink-0">
      <div
        className={cn(
          'bg-card border-border hover:border-primary w-44 overflow-hidden rounded-xl border transition-colors',
        )}
      >
        {/* Image strip */}
        <div className="relative h-28 w-full overflow-hidden bg-[#111]">
          <ImageWithSkeleton
            src={imageUrl}
            alt=""
            className={cn('h-full w-full', hasRealImage ? 'object-cover' : 'object-contain p-3')}
          />
          {hasRealImage && (
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          )}
        </div>

        {/* Stub info */}
        <div className="space-y-1 px-3 py-2.5">
          <div className="flex items-center justify-between gap-1">
            <p className="text-muted-foreground font-mono text-xs">
              #{ticket.id.slice(0, 8).toUpperCase()}
            </p>
            {badgeReady && (
              <StatusChip
                label={t(`tickets.ticket.states.${displayState}`)}
                variant={displayState}
              />
            )}
          </div>
          {total > 1 && (
            <p className="text-muted-foreground text-[10px]">
              {index + 1} of {total}
            </p>
          )}
        </div>
      </div>
    </Link>
  )
}

interface Props {
  tickets: Ticket[]
}

export function ReservationRow({ tickets }: Props) {
  const navigate = useNavigate()
  const sorted = tickets
    .slice()
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  const first = sorted[0]!
  const { data: event } = useEvent(first.event_id)
  const { data: reservation } = useReservation(first.reservation_id)
  const countdown = useCountdown(reservation?.expires_at)
  const imageUrl = getEventImageUrl(event?.image_url)
  const startDate = event?.starts_at ? new Date(event.starts_at) : null

  const awaitingPayment =
    reservation?.status === 'reserved' &&
    countdown > 0 &&
    tickets.some((t) => t.state === 'reserved')

  return (
    <div className="space-y-3">
      {/* Event header */}
      <div>
        {!event ? (
          <div className="space-y-1.5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
        ) : (
          <>
            <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {event.organisation?.name ?? 'Qrew'}
            </p>
            <h2 className="text-base leading-snug font-semibold">{event.name}</h2>
            <div className="text-muted-foreground mt-1 flex flex-wrap gap-3 text-xs">
              {event.venue && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3 shrink-0" />
                  {[event.venue.name, event.venue.city].filter(Boolean).join(', ')}
                </span>
              )}
              {startDate && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3 shrink-0" />
                  {startDate.toLocaleDateString('en-GB', {
                    weekday: 'short',
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Payment banner for reserved rows */}
      {awaitingPayment && (
        <div className="flex items-center justify-between gap-3">
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
            <span className="text-muted-foreground text-xs">remaining</span>
          </div>
          <button
            onClick={() =>
              void navigate({
                to: '/reservations/$reservationId',
                params: { reservationId: first.reservation_id },
              })
            }
            className="flex h-8 items-center gap-1.5 rounded-full bg-yellow-500 px-4 text-xs font-semibold text-black"
          >
            <CreditCard className="h-3.5 w-3.5 shrink-0" />
            Complete Payment
          </button>
        </div>
      )}

      {/* Carousel */}
      <div className="flex scrollbar-none gap-3 overflow-x-auto pb-1">
        {sorted.map((ticket, i) => (
          <TicketStub
            key={ticket.id}
            ticket={ticket}
            index={i}
            total={sorted.length}
            imageUrl={imageUrl}
            hasRealImage={!!event?.image_url}
          />
        ))}
      </div>
    </div>
  )
}
