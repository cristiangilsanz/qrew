import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ArrowRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EventCard } from '@/features/events/components/EventCard'
import { useEvents } from '@/features/events/hooks/useEvents'
import { useProfile } from '@/features/profile/hooks/useProfile'
import { TicketCard } from '@/features/tickets/components/TicketCard'
import { useTickets } from '@/features/tickets/hooks/useTickets'

export const Route = createFileRoute('/_app/home/')({
  component: HomePage,
})

function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'home.greetingMorning'
  if (h < 18) return 'home.greetingAfternoon'
  return 'home.greetingEvening'
}

const ACTIVE_STATES = ['reserved', 'issued', 'entry_pending']

function HomePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: profile } = useProfile()
  const { data: eventsData, isLoading: eventsLoading } = useEvents({})
  const { data: tickets, isLoading: ticketsLoading } = useTickets()

  const firstName = profile?.full_name?.split(' ')[0] ?? ''
  const upcomingEvents = eventsData?.items.slice(0, 3) ?? []
  const activeTickets = tickets?.filter((t) => ACTIVE_STATES.includes(t.state)) ?? []

  return (
    <div className="space-y-8 px-4 pt-8 pb-4">
      {/* Greeting */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          {t(greeting())}
          {firstName ? `, ${firstName}` : ''}
        </h1>
        <p className="text-muted-foreground text-sm">{t('home.subtitle')}</p>
      </div>

      {/* Upcoming Events */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">{t('home.upcomingEvents')}</h2>
          <button
            onClick={() => void navigate({ to: '/events' })}
            className="text-primary flex items-center gap-1 text-sm"
          >
            {t('home.seeAll')}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {eventsLoading && (
          <div className="flex justify-center py-8">
            <div className="border-primary h-6 w-6 animate-spin rounded-full border-2 border-t-transparent" />
          </div>
        )}

        {!eventsLoading && upcomingEvents.length === 0 && (
          <p className="text-muted-foreground py-4 text-center text-sm">{t('home.noEvents')}</p>
        )}

        <div className="space-y-3">
          {upcomingEvents.map((event) => (
            <EventCard
              key={event.id}
              event={event}
              onClick={() =>
                void navigate({ to: '/events/$eventId', params: { eventId: event.id } })
              }
            />
          ))}
        </div>
      </section>

      {/* Active Tickets */}
      {!ticketsLoading && activeTickets.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">{t('home.activeTickets')}</h2>
            <button
              onClick={() => void navigate({ to: '/tickets' })}
              className="text-primary flex items-center gap-1 text-sm"
            >
              {t('home.seeAll')}
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="space-y-3">
            {activeTickets.slice(0, 2).map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
