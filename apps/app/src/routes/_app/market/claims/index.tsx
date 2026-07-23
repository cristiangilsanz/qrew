import { createFileRoute, Link } from '@tanstack/react-router'
import { Calendar, Clock, MapPin, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { usePendingMarketAssignment } from '@/features/market/hooks/useMarketAssignment'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/claims/')({
  component: ClaimsPage,
})

function formatSeconds(s: number) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function AssignmentCard() {
  const { t } = useTranslation()
  const { data: assignment, isLoading } = usePendingMarketAssignment()
  const { data: event } = useEvent(assignment?.event_id ?? '')
  const countdown = useCountdown(assignment?.state === 'pending' ? assignment.expires_at : null)

  if (isLoading) {
    return <EventCardSkeleton />
  }

  if (!assignment) return null

  const expired = countdown === 0
  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? assignment.event_name ?? t('market.resaleMarket')

  return (
    <Link
      to="/market/assignments/$assignmentId"
      params={{ assignmentId: assignment.id }}
      className="block"
    >
      <article className="bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors">
        <div className="relative h-44 w-full overflow-hidden bg-[#111]">
          <ImageWithSkeleton
            src={imageUrl}
            alt={eventName}
            className={cn(
              'h-full w-full',
              event?.image_url ? 'object-cover' : 'object-contain p-4',
            )}
          />
          {event?.image_url && (
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          )}
          <div
            className={cn(
              'absolute top-3 right-3 flex items-center gap-1.5 rounded-full px-2.5 py-1 backdrop-blur-sm',
              expired ? 'bg-red-500/80' : 'bg-black/60',
            )}
          >
            <Clock className="h-3 w-3 text-white" />
            <span className="font-mono text-xs font-semibold text-white">
              {expired ? t('tickets.ticket.timeline.expired') : formatSeconds(countdown)}
            </span>
          </div>
        </div>
        <div className="space-y-2 p-4">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            {event?.organisation?.name ?? t('market.resaleMarket')}
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
  )
}

function ClaimsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: assignment, isLoading } = usePendingMarketAssignment()
  const { data: event } = useEvent(assignment?.event_id ?? '')

  const eventName = event?.name ?? assignment?.event_name ?? ''
  const matches = !query || eventName.toLowerCase().includes(query.toLowerCase())

  return (
    <div className="mx-auto min-h-screen max-w-[430px] space-y-4 px-4 pt-5 pb-28">
      <div>
        <BackButton to="/market" />
        <h1 className="mt-3 text-2xl font-bold">{t('market.myTicketsToClaim')}</h1>
      </div>

      {!isLoading && !!assignment && (
        <div className="relative">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            placeholder={t('market.searchByEvent')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pr-4 pl-9 text-sm text-white placeholder:text-white/30 focus:border-white/20 focus:outline-none"
          />
        </div>
      )}

      {isLoading && <EventCardSkeleton />}

      {!isLoading && (!assignment || !matches) && (
        <p className="text-muted-foreground pt-10 text-center text-sm">
          {query ? t('market.noResults') : t('market.noPendingClaims')}
        </p>
      )}

      {!isLoading && assignment && matches && <AssignmentCard />}
    </div>
  )
}
