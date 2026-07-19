import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Dialog } from '@/components/ui/dialog'
import { OrgCardSkeleton } from '@/components/ui/skeleton'
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
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <h1 className="text-2xl font-semibold">{t('organiser.title')}</h1>

      {isLoading && (
        <div className="grid gap-4">
          {[0, 1].map((i) => (
            <OrgCardSkeleton key={i} />
          ))}
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

      {/* FAB */}
      <button
        onClick={() => setShowCreate(true)}
        className="bg-primary hover:bg-primary/90 fixed bottom-24 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        style={{ right: 'max(calc((100vw - 430px) / 2 + 1.5rem), 1.5rem)' }}
      >
        <Plus className="h-5 w-5 shrink-0" />
        <span className="text-sm font-semibold">{t('organiser.org.create')}</span>
      </button>

      <Dialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title={t('organiser.org.createTitle')}
      >
        <CreateOrganisationForm
          onSuccess={(id) => {
            setShowCreate(false)
            void navigate({ to: '/organiser/$orgId', params: { orgId: id } })
          }}
        />
      </Dialog>
    </div>
  )
}
