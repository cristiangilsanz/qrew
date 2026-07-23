import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { TicketTypeListSkeleton } from '@/components/ui/skeleton'
import { TicketTypeList } from '@/features/organiser/components/TicketTypeList'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'

export const Route = createFileRoute('/_app/organiser/$orgId/events/$eventId/tickets')({
  component: EditTicketsPage,
})

function EditTicketsPage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()
  const { data, isLoading } = useOrgEvents(orgId)
  const event = data?.items.find((e) => e.id === eventId)

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton
        to="/organiser/$orgId/events/$eventId/"
        params={{ orgId, eventId }}
      />
      <h1 className="text-2xl font-semibold">{t('organiser.ticketTypes.title')}</h1>

      {(isLoading || !event) ? (
        <TicketTypeListSkeleton />
      ) : (
        <TicketTypeList eventId={eventId} eventStatus={event.status} />
      )}
    </div>
  )
}
