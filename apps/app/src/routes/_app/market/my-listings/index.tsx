import { createFileRoute, Link } from '@tanstack/react-router'
import { Calendar, MapPin, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import type { Ticket } from '@/features/tickets/api'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/my-listings/')({
  component: MyListingsPage,
})

function ListingCard({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation()
  const { data: event } = useEvent(ticket.event_id)
  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? t('market.resaleMarket')

  return (
    <Link to="/tickets/$ticketId" params={{ ticketId: ticket.id }} className="block">
      <article className="bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors">
        <div className="relative h-44 w-full overflow-hidden bg-[#111]">
          <ImageWithSkeleton
            src={imageUrl}
            alt={eventName}
            className={cn('h-full w-full', event?.image_url ? 'object-cover' : 'object-contain p-4')}
          />
          {event?.image_url && (
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          )}
        </div>
        <div className="space-y-2 p-4">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            {event?.organisation?.name ?? t('market.resaleMarket')}
          </p>
          <h2 className="text-base font-semibold leading-snug">{eventName}</h2>
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
                  weekday: 'short', day: 'numeric', month: 'short',
                  hour: '2-digit', minute: '2-digit',
                })}
              </span>
            )}
          </div>
        </div>
      </article>
    </Link>
  )
}

function MyListingsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: tickets, isLoading } = useTickets()
  const listedTickets = (tickets ?? []).filter((t) => t.state === 'on_sale')

  const filtered = query
    ? listedTickets.filter((t) => t.event_id.toLowerCase().includes(query.toLowerCase()))
    : listedTickets

  return (
    <div className="mx-auto min-h-screen max-w-[430px] px-4 pt-5 pb-28 space-y-4">
      <div>
        <BackButton to="/market" />
        <h1 className="mt-3 text-2xl font-bold">{t('market.myTicketsOnSale')}</h1>
      </div>

      {!isLoading && listedTickets.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            placeholder={t('market.searchByEvent')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-9 pr-4 text-sm text-white placeholder:text-white/30 focus:border-white/20 focus:outline-none"
          />
        </div>
      )}

      {isLoading && (
        <div className="space-y-4">
          <EventCardSkeleton />
          <EventCardSkeleton />
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
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
