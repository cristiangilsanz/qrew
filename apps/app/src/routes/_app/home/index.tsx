import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import homeHero from '@/assets/images/home.jpg'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { EventCard } from '@/features/events/components/EventCard'
import { useEvents } from '@/features/events/hooks/useEvents'
import { useProfile } from '@/features/profile/hooks/useProfile'

export const Route = createFileRoute('/_app/home/')({
  component: HomePage,
})

function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'home.greetingMorning'
  if (h < 18) return 'home.greetingAfternoon'
  return 'home.greetingEvening'
}

function HomePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: profile } = useProfile()
  const { data: eventsData, isLoading: eventsLoading } = useEvents({})

  const rawFirst = profile?.full_name?.split(' ')[0] ?? ''
  const firstName = rawFirst ? rawFirst[0].toUpperCase() + rawFirst.slice(1) : ''
  const upcomingEvents = (eventsData?.items ?? [])
    .slice()
    .sort((a, b) => {
      if (!a.starts_at) return 1
      if (!b.starts_at) return -1
      return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime()
    })
    .slice(0, 3)

  return (
    <div className="space-y-4 pb-4">
      {/* Greeting + Hero — full bleed, no padding, no rounding */}
      <div className="relative h-96 overflow-hidden">
        <img
          src={homeHero}
          alt=""
          className="absolute inset-0 h-full w-full object-cover object-center opacity-60"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/20 to-[hsl(0,0%,10%)]" />
        <div className="absolute inset-x-0 top-0 space-y-1 px-5 pt-6">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            {t(greeting())}
            {firstName ? (
              <>
                , <span className="text-primary">{firstName}</span>
              </>
            ) : (
              ''
            )}
          </h1>
          <p className="text-sm text-white/70">{t('home.subtitle')}</p>
        </div>
        <div className="absolute inset-x-0 bottom-0 px-5 pb-12">
          <p className="text-2xl leading-tight font-bold tracking-tight text-white">
            Your next experience
            <br />
            is waiting for you.
          </p>
        </div>
      </div>

      {/* Upcoming Events */}
      <section className="space-y-3 px-4 pb-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">{t('home.upcomingEvents')}</h2>
          <button
            onClick={() => void navigate({ to: '/events' })}
            className="bg-primary hover:bg-primary/90 flex h-10 w-10 items-center justify-center rounded-full text-white transition-colors"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {eventsLoading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <EventCardSkeleton key={i} />
            ))}
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
    </div>
  )
}
