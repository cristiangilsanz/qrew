import { createFileRoute, Link } from '@tanstack/react-router'
import { Ticket } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { TicketState } from '@/features/tickets/api'
import { TicketCard } from '@/features/tickets/components/TicketCard'
import { useTickets } from '@/features/tickets/hooks/useTickets'

export const Route = createFileRoute('/_app/tickets/')({
  component: TicketsPage,
})

const ACTIVE_STATES: TicketState[] = ['reserved', 'issued', 'entry_pending']

function TicketsPage() {
  const { t } = useTranslation()
  const { data: tickets, isLoading } = useTickets()

  const active = tickets?.filter((ticket) => ACTIVE_STATES.includes(ticket.state)) ?? []
  const past = tickets?.filter((ticket) => !ACTIVE_STATES.includes(ticket.state)) ?? []

  return (
    <div className="space-y-6 p-4">
      <h1 className="text-2xl font-bold">{t('tickets.title')}</h1>

      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        </div>
      )}

      {!isLoading && tickets?.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-12 text-center">
          <Ticket className="text-muted-foreground h-12 w-12" />
          <p className="text-muted-foreground">{t('tickets.empty')}</p>
          <Link
            to="/events"
            className="text-primary hover:text-primary/80 text-sm underline underline-offset-4"
          >
            {t('tickets.browseEvents')}
          </Link>
        </div>
      )}

      {active.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-muted-foreground text-sm font-medium tracking-wide uppercase">
            {t('tickets.sections.active')}
          </h2>
          {active.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </section>
      )}

      {past.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-muted-foreground text-sm font-medium tracking-wide uppercase">
            {t('tickets.sections.past')}
          </h2>
          {past.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </section>
      )}
    </div>
  )
}
