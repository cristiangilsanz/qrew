import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EventDetailCard } from '@/features/events/components/EventDetailCard'
import { useEvent } from '@/features/events/hooks/useEvent'

export const Route = createFileRoute('/_app/events/$eventId')({
  component: EventDetailPage,
})

function EventDetailPage() {
  const { t } = useTranslation()
  const { eventId } = Route.useParams()
  const { data: event, isLoading, isError } = useEvent(eventId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  if (isError || !event) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-muted-foreground">{t('events.notFound')}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <Link
        to="/events"
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('events.backToList')}
      </Link>
      <EventDetailCard event={event} />
    </div>
  )
}
