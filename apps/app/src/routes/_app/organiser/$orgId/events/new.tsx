import { createFileRoute, useNavigate } from '@tanstack/react-router'

import { BackButton } from '@/components/ui/back-button'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CreateEventForm } from '@/features/organiser/components/CreateEventForm'

export const Route = createFileRoute('/_app/organiser/$orgId/events/new')({
  component: NewEventPage,
})

function NewEventPage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <BackButton to="/organiser/$orgId" params={{ orgId }} />
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('organiser.events.create')}</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateEventForm
            orgId={orgId}
            onSuccess={(eventId) =>
              void navigate({
                to: '/organiser/$orgId/events/$eventId',
                params: { orgId, eventId },
              })
            }
          />
        </CardContent>
      </Card>
    </div>
  )
}
