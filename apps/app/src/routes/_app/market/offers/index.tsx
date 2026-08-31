// implements claims
import { useQueries } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { Calendar, Clock, MapPin, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { EmptyMessage } from '@/components/ui/empty-message'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { PageError } from '@/components/ui/page-error'
import { SEARCH_ICON_CLASS, SEARCH_INPUT_CLASS } from '@/components/ui/search-field'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { type EventDetail, eventsApi } from '@/features/events/api'
import type { MarketOfferResponse } from '@/features/market/api'
import { useMarketOffers } from '@/features/market/hooks/useMarketOffer'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/offers/')({
  component: ClaimsPage,
})

// implements format seconds
function formatSeconds(s: number) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

interface CardProps {
  assignment: MarketOfferResponse
  event?: EventDetail
}

// renders the assignment card component
function AssignmentCard({ assignment, event }: CardProps) {
  const { t } = useTranslation()
  const countdown = useCountdown(assignment.state === 'pending' ? assignment.expires_at : undefined)

  // a claim whose countdown ran out reads as expired before its row catches up
  const timedOut = assignment.state === 'pending' && countdown === 0
  const effectiveState = timedOut ? 'expired' : assignment.state
  const isPending = assignment.state === 'pending' && !timedOut
  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? assignment.event_name ?? t('market.resaleMarket')

  // implements state label
  const stateLabel =
    effectiveState === 'paid'
      ? t('market.offers.paidBadge')
      : effectiveState === 'declined'
        ? t('market.offers.declinedBadge')
        : t('market.offers.expiredBadge')

  return (
    <Link to="/market/offers/$offerId" params={{ offerId: assignment.id }} className="block">
      <article
        className={cn(
          'bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors',
          !isPending && 'opacity-60',
        )}
      >
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
          {isPending && (
            <div className="absolute top-3 right-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 backdrop-blur-sm">
              <Clock className="h-3 w-3 text-white" />
              <span className="font-mono text-xs font-semibold text-white">
                {formatSeconds(countdown)}
              </span>
            </div>
          )}
        </div>
        <div className="space-y-2 p-4">
          <div className="flex items-start justify-between gap-3">
            <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {event?.organisation?.name ?? t('market.resaleMarket')}
            </p>
            {!isPending && <StatusChip label={stateLabel} variant={effectiveState} />}
          </div>
          <h2 className="text-base leading-snug font-semibold">{eventName}</h2>
          <div className="text-muted-foreground flex flex-wrap gap-3 text-xs">
            {event?.venue.city && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 shrink-0" />
                {event.venue.city}
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

// renders the claims page component
function ClaimsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: assignments = [], isLoading, isError, refetch } = useMarketOffers()

  const eventQueries = useQueries({
    queries: assignments.map((assignment) => ({
      queryKey: ['events', assignment.event_id],
      // implements query fn
      queryFn: () => eventsApi.getById(assignment.event_id),
      enabled: !!assignment.event_id,
    })),
  })

  const term = query.trim().toLowerCase()
  const rows = assignments
    .map((assignment, index) => ({ assignment, event: eventQueries[index]?.data }))
    .filter(({ assignment, event }) => {
      if (!term) return true
      const name = event?.name ?? assignment.event_name ?? ''
      return name.toLowerCase().includes(term)
    })

  if (isError) return <PageError onRetry={() => void refetch()} />

  return (
    <div className="mx-auto max-w-[430px] space-y-4 px-4 pt-5 pb-28">
      <BackButton to="/market" />
      <h1 className="text-2xl font-bold">{t('market.myOffers')}</h1>

      {!isLoading && assignments.length > 0 && (
        <div className="relative">
          <Search className={SEARCH_ICON_CLASS} />
          <input
            type="text"
            placeholder={t('market.searchByEvent')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={SEARCH_INPUT_CLASS}
          />
        </div>
      )}

      {isLoading && <EventCardSkeleton />}

      {!isLoading && !isError && rows.length === 0 && (
        <EmptyMessage>{term ? t('market.noResults') : t('market.noPendingOffers')}</EmptyMessage>
      )}

      {!isLoading &&
        !isError &&
        rows.map(({ assignment, event }) => (
          <AssignmentCard key={assignment.id} assignment={assignment} event={event} />
        ))}
    </div>
  )
}
