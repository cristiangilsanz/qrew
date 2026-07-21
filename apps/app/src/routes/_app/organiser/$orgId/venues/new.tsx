import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CreateVenueForm } from '@/features/organiser/components/CreateVenueForm'

export const Route = createFileRoute('/_app/organiser/$orgId/venues/new')({
  component: NewVenuePage,
})

function NewVenuePage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <BackButton to="/organiser/$orgId" params={{ orgId }} />
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('organiser.venues.createTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateVenueForm
            onSuccess={() => void navigate({ to: '/organiser/$orgId', params: { orgId } })}
          />
        </CardContent>
      </Card>
    </div>
  )
}
