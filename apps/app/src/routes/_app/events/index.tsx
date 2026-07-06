import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

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
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">{t('events.title')}</h1>
      <EventFiltersBar onFiltersChange={setFilters} />
      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        </div>
      )}
      {!isLoading && data?.items.length === 0 && (
        <p className="text-muted-foreground py-12 text-center">{t('events.empty')}</p>
      )}
      <div className="grid gap-4">
        {data?.items.map((event) => (
          <EventCard
            key={event.id}
            event={event}
            onClick={() => void navigate({ to: '/events/$eventId', params: { eventId: event.id } })}
          />
        ))}
      </div>
    </div>
  )
}
