import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { EventCardSkeleton } from '@/components/ui/skeleton'
import { type EventFilters } from '@/features/events/api'
import { EventCard } from '@/features/events/components/EventCard'
import { EventFiltersBar } from '@/features/events/components/EventFiltersBar'
import { useEvents } from '@/features/events/hooks/useEvents'

export const Route = createFileRoute('/_app/events/')({
  component: EventsPage,
})

function EventsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [filters, setFilters] = useState<EventFilters>({})
  const { data, isLoading } = useEvents(filters)

  return (
    <div className="space-y-6 p-4">
      <h1 className="text-2xl font-semibold">{t('events.title')}</h1>
      <EventFiltersBar onFiltersChange={setFilters} />
      {!isLoading && data?.items.length === 0 && (
        <p className="text-muted-foreground py-12 text-center">{t('events.empty')}</p>
      )}
      <div className="grid gap-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <EventCardSkeleton key={i} />)
          : data?.items.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                onClick={() =>
                  void navigate({ to: '/events/$eventId', params: { eventId: event.id } })
                }
              />
            ))}
      </div>
    </div>
  )
}
