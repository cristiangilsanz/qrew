import { createFileRoute, Link } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import noTicketsImg from '@/assets/images/no-tickets.png'

import { TicketCardSkeleton } from '@/components/ui/skeleton'

import type { Ticket } from '@/features/tickets/api'
import { ReservationRow } from '@/features/tickets/components/ReservationRow'
import { useTickets } from '@/features/tickets/hooks/useTickets'

export const Route = createFileRoute('/_app/tickets/')({
  component: TicketsPage,
})

function groupByReservation(tickets: Ticket[]): Map<string, Ticket[]> {
  const map = new Map<string, Ticket[]>()
  for (const ticket of tickets) {
    const group = map.get(ticket.reservation_id) ?? []
    group.push(ticket)
    map.set(ticket.reservation_id, group)
  }
  return map
}

function TicketsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: tickets, isLoading } = useTickets()

  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ['tickets'] })
  }, [])

  const sorted = (tickets ?? [])
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  const groups = groupByReservation(sorted)
  const reservationIds = [...new Set(sorted.map((t) => t.reservation_id))]

  return (
    <div className="space-y-6 p-4 pb-24">
      <h1 className="text-2xl font-bold">{t('tickets.title')}</h1>

      {isLoading && (
        <div className="flex flex-col gap-6">
          {[0, 1, 2].map((i) => (
            <TicketCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && tickets?.length === 0 && (
        <div className="flex min-h-[70vh] flex-col items-center justify-center gap-6 px-6 text-center">
          <img
            src={noTicketsImg}
            alt="No tickets yet"
            className="max-h-[35vh] w-auto object-contain"
          />
          <Link
            to="/events"
            className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-11 items-center rounded-full px-6 text-sm font-semibold transition-colors"
          >
            {t('tickets.browseEvents')}
          </Link>
        </div>
      )}

      {reservationIds.length > 0 && (
        <div className="flex flex-col gap-8">
          {reservationIds.map((reservationId) => (
            <ReservationRow key={reservationId} tickets={groups.get(reservationId)!} />
          ))}
        </div>
      )}
    </div>
  )
}
