import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { CreateVenueForm } from '@/features/organiser/components/CreateVenueForm'

export const Route = createFileRoute('/_app/organiser/$orgId/venues/new')({
  component: NewVenuePage,
})

function NewVenuePage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/organiser/$orgId" params={{ orgId }} />
      <h1 className="text-2xl font-semibold">{t('organiser.venues.createTitle')}</h1>
      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
        <CreateVenueForm
          onSuccess={() => void navigate({ to: '/organiser/$orgId', params: { orgId } })}
        />
      </div>
    </div>
  )
}
