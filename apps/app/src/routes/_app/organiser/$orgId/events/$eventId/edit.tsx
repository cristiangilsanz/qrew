import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { FormPageSkeleton } from '@/components/ui/skeleton'
import { CancelEventSection } from '@/features/organiser/components/CancelEventSection'
import { EditEventForm } from '@/features/organiser/components/EditEventForm'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'

export const Route = createFileRoute('/_app/organiser/$orgId/events/$eventId/edit')({
  component: EditEventPage,
})

function EditEventPage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()
  const { data } = useOrgEvents(orgId)
  const event = data?.items.find((e) => e.id === eventId)

  if (!event) return <FormPageSkeleton />

  const showCancel = event.status === 'draft' || event.status === 'published'

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton
        to="/organiser/$orgId/events/$eventId/"
        params={{ orgId, eventId }}
      />
      <h1 className="text-2xl font-semibold">{t('organiser.events.edit')}</h1>
      <EditEventForm event={event} orgId={orgId} />

      {showCancel && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-red-500/20 bg-red-500/5">
          <CancelEventSection event={event} orgId={orgId} />
        </div>
      )}
    </div>
  )
}
