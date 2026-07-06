import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
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
      <Link
        to="/organiser/$orgId"
        params={{ orgId }}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('organiser.backToOrg')}
      </Link>
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
