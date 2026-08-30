// implements my listings
import { createFileRoute, Link } from '@tanstack/react-router'
import { Calendar, MapPin, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { PageError } from '@/components/ui/page-error'
import { SEARCH_ICON_CLASS, SEARCH_INPUT_CLASS } from '@/components/ui/search-field'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import type { Ticket } from '@/features/tickets/api'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/my-listings/')({
  component: MyListingsPage,
})

// renders the listing card component
function ListingCard({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation()
  const { data: event, isLoading: eventLoading } = useEvent(ticket.event_id)

  if (eventLoading) return <EventCardSkeleton />

  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? t('market.resaleMarket')

  return (
    <Link to="/tickets/$ticketId" params={{ ticketId: ticket.id }} className="block">
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
        </div>
        <div className="space-y-2 p-4">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            {event?.organisation?.name ?? t('market.resaleMarket')}
          </p>
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

// renders the my listings page component
function MyListingsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: tickets, isLoading, isError, refetch } = useTickets()
  // implements listed tickets
  const listedTickets = (tickets ?? []).filter((t) => t.state === 'on_sale')

  const filtered = query
    ? listedTickets.filter((t) => t.event_id.toLowerCase().includes(query.toLowerCase()))
    : listedTickets

  if (isError) return <PageError onRetry={() => void refetch()} />

  return (
    <div className="mx-auto max-w-[430px] space-y-4 px-4 pt-5 pb-28">
      <BackButton to="/market" />
      <h1 className="text-2xl font-bold">{t('market.myTicketsOnSale')}</h1>

      {!isLoading && listedTickets.length > 0 && (
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

      {isLoading && (
        <div className="space-y-4">
          <EventCardSkeleton />
          <EventCardSkeleton />
        </div>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <p className="text-muted-foreground pt-10 text-center text-sm">
          {query ? t('market.noResults') : t('market.noTicketsOnSale')}
        </p>
      )}

      <div className="space-y-4">
        {filtered.map((ticket) => (
          <ListingCard key={ticket.id} ticket={ticket} />
        ))}
      </div>
    </div>
  )
}
