// implements tickets
import { useQueries, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { EmptyMessage } from '@/components/ui/empty-message'
import { PageError } from '@/components/ui/page-error'
import {
  SEARCH_CLEAR_CLASS,
  SEARCH_ICON_CLASS,
  SEARCH_INPUT_CLASS,
} from '@/components/ui/search-field'
import { ReservationRowSkeleton } from '@/components/ui/skeleton'
import { eventsApi } from '@/features/events/api'
import type { Ticket } from '@/features/tickets/api'
import { ReservationRow } from '@/features/tickets/components/ReservationRow'
import { useTickets } from '@/features/tickets/hooks/useTickets'

export const Route = createFileRoute('/_app/tickets/')({
  component: TicketsPage,
})

// implements group by reservation
function groupByReservation(tickets: Ticket[]): Map<string, Ticket[]> {
  const map = new Map<string, Ticket[]>()
  for (const ticket of tickets) {
    const group = map.get(ticket.reservation_id) ?? []
    group.push(ticket)
    map.set(ticket.reservation_id, group)
  }
  return map
}

// renders the tickets page component
function TicketsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const {
    data: tickets,
    isLoading: ticketsLoading,
    isError: ticketsError,
    refetch: refetchTickets,
  } = useTickets()

  const [query, setQuery] = useState('')

  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ['tickets'] })
  }, [queryClient])

  // implements sorted
  const sorted = (tickets ?? [])
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  const eventIds = [...new Set(sorted.map((t) => t.event_id))]

  const eventQueries = useQueries({
    queries: eventIds.map((id) => ({
      queryKey: ['events', id],
      // implements query fn
      queryFn: () => eventsApi.getById(id),
      enabled: !ticketsLoading && !!id,
    })),
  })

  // implements events loading
  const eventsLoading = eventQueries.some((q) => q.isLoading)
  const isLoading = ticketsLoading || (eventIds.length > 0 && eventsLoading)

  const eventMap = new Map(
    eventQueries
      .map((q) => q.data)
      .filter(Boolean)
      .map((e) => [e!.id, e!]),
  )

  const term = query.trim().toLowerCase()
  const matching = term
    ? sorted.filter((t) => (eventMap.get(t.event_id)?.name ?? '').toLowerCase().includes(term))
    : sorted
  const groups = groupByReservation(matching)
  const reservationIds = [...new Set(matching.map((t) => t.reservation_id))]

  if (ticketsError) return <PageError onRetry={() => void refetchTickets()} />

  return (
    <div className="space-y-6 px-4 pt-5 pb-24">
      <h1 className="text-2xl font-bold">{t('tickets.title')}</h1>

      {!isLoading && sorted.length > 0 && (
        <div className="relative">
          <Search className={SEARCH_ICON_CLASS} />
          <input
            type="text"
            placeholder={t('market.searchByEvent')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={SEARCH_INPUT_CLASS}
          />
          {query && (
            <button type="button" onClick={() => setQuery('')} className={SEARCH_CLEAR_CLASS}>
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {isLoading && (
        <div className="flex flex-col gap-8">
          {[0, 1, 2].map((i) => (
            <ReservationRowSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && !ticketsError && sorted.length > 0 && matching.length === 0 && (
        <EmptyMessage>{t('market.noResults')}</EmptyMessage>
      )}

      {!isLoading && !ticketsError && sorted.length === 0 && (
        <EmptyMessage
          action={
            <Link
              to="/events"
              className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-10 items-center rounded-full px-6 text-sm font-semibold transition-colors"
            >
              <Search className="mr-2 h-4 w-4" />
              {t('tickets.browseEvents')}
            </Link>
          }
        >
          {t('tickets.empty')}
        </EmptyMessage>
      )}

      {!isLoading && reservationIds.length > 0 && (
        <div className="flex flex-col gap-8">
          {reservationIds.map((reservationId) => (
            <ReservationRow
              key={reservationId}
              tickets={groups.get(reservationId)!}
              event={eventMap.get(groups.get(reservationId)![0]!.event_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
