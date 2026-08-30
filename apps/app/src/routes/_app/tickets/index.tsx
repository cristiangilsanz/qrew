// implements tickets
import { useQueries, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { Search } from 'lucide-react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { PageError } from '@/components/ui/page-error'
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

  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ['tickets'] })
  }, [])

  // implements sorted
  const sorted = (tickets ?? [])
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  const groups = groupByReservation(sorted)
  const reservationIds = [...new Set(sorted.map((t) => t.reservation_id))]
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

  if (ticketsError) return <PageError onRetry={() => void refetchTickets()} />

  return (
    <div className="space-y-6 px-4 pt-5 pb-24">
      <h1 className="text-2xl font-bold">{t('tickets.title')}</h1>

      {isLoading && (
        <div className="flex flex-col gap-8">
          {[0, 1, 2].map((i) => (
            <ReservationRowSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && !ticketsError && tickets?.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-12 text-center">
          <p className="text-muted-foreground text-sm">{t('tickets.empty')}</p>
          <Link
            to="/events"
            className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-10 items-center rounded-full px-6 text-sm font-semibold transition-colors"
          >
            <Search className="mr-2 h-4 w-4" />
            {t('tickets.browseEvents')}
          </Link>
        </div>
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
