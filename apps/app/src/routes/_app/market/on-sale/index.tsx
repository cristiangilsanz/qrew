// implements my listings
import { useQueries } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { EmptyMessage } from '@/components/ui/empty-message'
import { PageError } from '@/components/ui/page-error'
import { SEARCH_ICON_CLASS, SEARCH_INPUT_CLASS } from '@/components/ui/search-field'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { eventsApi } from '@/features/events/api'
import { ReservationRow } from '@/features/tickets/components/ReservationRow'
import { useTickets } from '@/features/tickets/hooks/useTickets'

export const Route = createFileRoute('/_app/market/on-sale/')({
  component: MyListingsPage,
})

// renders the my listings page component
function MyListingsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: tickets, isLoading, isError, refetch } = useTickets()
  // implements listed tickets
  const listedTickets = (tickets ?? []).filter((t) => t.state === 'on_sale')

  const eventIds = [...new Set(listedTickets.map((t) => t.event_id))]
  const eventQueries = useQueries({
    // implements queries
    queries: eventIds.map((id) => ({
      queryKey: ['events', id],
      queryFn: () => eventsApi.getById(id),
      enabled: !!id,
    })),
  })
  const eventMap = new Map(
    eventQueries
      .map((q) => q.data)
      .filter(Boolean)
      .map((e) => [e!.id, e!]),
  )

  const term = query.trim().toLowerCase()
  const filtered = term
    ? listedTickets.filter((t) =>
        (eventMap.get(t.event_id)?.name ?? '').toLowerCase().includes(term),
      )
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
        <EmptyMessage>{query ? t('market.noResults') : t('market.noTicketsOnSale')}</EmptyMessage>
      )}

      {filtered.length > 0 && (
        <div className="flex flex-col gap-8">
          {filtered.map((ticket) => (
            <ReservationRow
              key={ticket.id}
              tickets={[ticket]}
              event={eventMap.get(ticket.event_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
