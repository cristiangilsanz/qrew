import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CreateOrganisationForm } from '@/features/organiser/components/CreateOrganisationForm'
import { OrgCard } from '@/features/organiser/components/OrgCard'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'

export const Route = createFileRoute('/_app/organiser/')({
  component: OrganiserPage,
})

function OrganiserPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useMyOrganisations()
  const orgs = data?.items ?? []

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('organiser.title')}</h1>
        <Button onClick={() => setShowCreate((v) => !v)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('organiser.org.create')}
        </Button>
      </div>
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('organiser.org.createTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
            <CreateOrganisationForm
              onSuccess={(id) => {
                setShowCreate(false)
                void navigate({ to: '/organiser/$orgId', params: { orgId: id } })
              }}
            />
          </CardContent>
        </Card>
      )}
      {isLoading && (
        <div className="flex justify-center py-8">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        </div>
      )}
      {!isLoading && orgs.length === 0 && !showCreate && (
        <p className="text-muted-foreground py-8 text-center text-sm">{t('organiser.org.empty')}</p>
      )}
      <div className="grid gap-4">
        {orgs.map((org) => (
          <OrgCard key={org.id} org={org} />
        ))}
      </div>
    </div>
  )
}
