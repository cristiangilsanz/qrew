import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
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
      <Link
        to="/organiser"
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('organiser.backToOrgs')}
      </Link>
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
