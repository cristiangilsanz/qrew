import { createFileRoute } from '@tanstack/react-router'

import { BackButton } from '@/components/ui/back-button'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { InviteMemberForm } from '@/features/organiser/components/InviteMemberForm'
import { OrgEventList } from '@/features/organiser/components/OrgEventList'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'

export const Route = createFileRoute('/_app/organiser/$orgId/')({
  component: OrgDashboardPage,
})

function OrgDashboardPage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()
  const { data } = useMyOrganisations()
  const org = data?.items.find((o) => o.id === orgId)

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <BackButton to="/organiser" />
      <h1 className="text-2xl font-semibold">{org?.name ?? t('organiser.org.loading')}</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('organiser.events.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <OrgEventList orgId={orgId} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('organiser.members.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <InviteMemberForm orgId={orgId} />
        </CardContent>
      </Card>
    </div>
  )
}
