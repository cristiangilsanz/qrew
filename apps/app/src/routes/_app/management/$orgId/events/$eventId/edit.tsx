import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { FormPageSkeleton } from '@/components/ui/skeleton'
import { CancelEventSection } from '@/features/organiser/components/CancelEventSection'
import { EditEventForm } from '@/features/organiser/components/EditEventForm'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'

export const Route = createFileRoute('/_app/management/$orgId/events/$eventId/edit')({
  component: EditEventPage,
})

function EditEventPage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()
  const { data, isLoading } = useOrgEvents(orgId)
  const event = data?.items.find((e) => e.id === eventId)

  const hasStarted = event?.status === 'ongoing'
  const showCancel =
    event && !hasStarted && (event.status === 'draft' || event.status === 'published')

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/management/$orgId/events/$eventId/" params={{ orgId, eventId }} />
      <h1 className="text-2xl font-semibold">{t('organiser.events.edit')}</h1>

      {isLoading || !event ? (
        <FormPageSkeleton />
      ) : hasStarted ? (
        <p className="text-muted-foreground text-sm">
          {t('organiser.events.notEditableAfterStart')}
        </p>
      ) : (
        <>
          <EditEventForm event={event} orgId={orgId} />
          {showCancel && (
            <div className="mt-4 overflow-hidden rounded-2xl border border-red-500/20 bg-red-500/5">
              <CancelEventSection event={event} orgId={orgId} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
