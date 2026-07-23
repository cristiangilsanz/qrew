import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { CreateOrganisationForm } from '@/features/organiser/components/CreateOrganisationForm'

export const Route = createFileRoute('/_app/organiser/new')({
  component: NewOrganisationPage,
})

function NewOrganisationPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/organiser" />
      <h1 className="text-2xl font-semibold">{t('organiser.org.createTitle')}</h1>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
        <CreateOrganisationForm
          onSuccess={(id) => void navigate({ to: '/organiser/$orgId', params: { orgId: id } })}
        />
      </div>
    </div>
  )
}
