import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { CreateEventForm } from '@/features/organiser/components/CreateEventForm'

export const Route = createFileRoute('/_app/organiser/$orgId/events/new')({
  component: NewEventPage,
})

function NewEventPage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/organiser/$orgId" params={{ orgId }} />
      <h1 className="text-2xl font-semibold">{t('organiser.events.create')}</h1>
      <CreateEventForm
        orgId={orgId}
        onSuccess={(eventId) =>
          void navigate({
            to: '/organiser/$orgId/events/$eventId',
            params: { orgId, eventId },
          })
        }
      />
    </div>
  )
}
