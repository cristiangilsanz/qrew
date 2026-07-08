import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useEvent } from '@/features/events/hooks/useEvent'
import { QueuePanel } from '@/features/tickets/components/QueuePanel'

export const Route = createFileRoute('/_app/events/$eventId/queue')({
  component: QueuePage,
})

function QueuePage() {
  const { t } = useTranslation()
  const { eventId } = Route.useParams()
  const navigate = useNavigate()
  const { data: event } = useEvent(eventId)

  if (event && !event.queue_required) {
    void navigate({ to: '/events/$eventId/checkout', params: { eventId }, replace: true })
    return null
  }

  return (
    <div className="mx-auto max-w-md space-y-6 p-6">
      <Link
        to="/events/$eventId"
        params={{ eventId }}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('events.backToEvent')}
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('tickets.queue.title')}</CardTitle>
          {event && <p className="text-muted-foreground text-sm">{event.name}</p>}
        </CardHeader>
        <CardContent>
          <QueuePanel eventId={eventId} />
        </CardContent>
      </Card>
    </div>
  )
}
