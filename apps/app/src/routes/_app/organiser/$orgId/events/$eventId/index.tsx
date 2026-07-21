import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EditEventForm } from '@/features/organiser/components/EditEventForm'
import { EventActions } from '@/features/organiser/components/EventActions'
import { TicketTypeList } from '@/features/organiser/components/TicketTypeList'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'

export const Route = createFileRoute('/_app/organiser/$orgId/events/$eventId/')({
  component: EventManagePage,
})

function EventManagePage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()
  const { data } = useOrgEvents(orgId)
  const event = data?.items.find((e) => e.id === eventId)

  if (!event) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <div className="flex justify-center py-8">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <BackButton to="/organiser/$orgId" params={{ orgId }} />
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{event.name}</h1>
        <EventActions event={event} orgId={orgId} />
      </div>
      {event.status === 'draft' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('organiser.events.edit')}</CardTitle>
          </CardHeader>
          <CardContent>
            <EditEventForm event={event} orgId={orgId} />
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('organiser.ticketTypes.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <TicketTypeList eventId={eventId} />
        </CardContent>
      </Card>
    </div>
  )
}
