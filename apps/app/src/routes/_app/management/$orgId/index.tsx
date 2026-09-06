// implements org id
import { createFileRoute, Link } from '@tanstack/react-router'
import { CalendarDays, ChevronRight, Trash2, Users } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { PageError } from '@/components/ui/page-error'
import { Skeleton } from '@/components/ui/skeleton'
import { useDeleteOrganisation } from '@/features/organiser/hooks/useDeleteOrganisation'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'
import { useOrgCollaborators } from '@/features/organiser/hooks/useOrgCollaborators'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'

export const Route = createFileRoute('/_app/management/$orgId/')({
  component: OrgDashboardPage,
})

// renders the org dashboard page component
function OrgDashboardPage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()

  const { data: orgsData, isLoading: orgLoading } = useMyOrganisations()
  // implements org
  const org = orgsData?.items.find((o) => o.id === orgId)

  const { data: collaboratorsData, isLoading: collaboratorsLoading } = useOrgCollaborators(orgId)
  const {
    data: eventsData,
    isLoading: eventsLoading,
    isError: eventsError,
    refetch: refetchEvents,
  } = useOrgEvents(orgId)

  const allLoading = orgLoading || eventsLoading || collaboratorsLoading
  const collaboratorCount = collaboratorsData?.length ?? 0
  const eventCount = eventsData?.items.length ?? 0

  const [deleteOpen, setDeleteOpen] = useState(false)
  const deleteOrg = useDeleteOrganisation()

  // opens the confirmation that removes the organisation
  const openDelete = () => setDeleteOpen(true)

  if (eventsError) return <PageError onRetry={() => void refetchEvents()} />

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/management" />
      <div>
        {allLoading ? (
          <div className="space-y-1.5">
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-4 w-24" />
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-semibold">{org?.name}</h1>
            {org?.slug && <p className="text-muted-foreground text-sm">@{org.slug}</p>}
          </>
        )}
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <Link
          to="/management/$orgId/events"
          params={{ orgId }}
          className="flex w-full items-center gap-3 px-4 py-4 transition-colors hover:bg-white/[0.04]"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
            <CalendarDays className="h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('organiser.events.title')}</span>
          {allLoading ? (
            <Skeleton className="h-5 w-6 rounded-full" />
          ) : (
            eventCount > 0 && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">
                {eventCount}
              </span>
            )
          )}
          <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
        </Link>
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <Link
          to="/management/$orgId/collaborators"
          params={{ orgId }}
          className="flex w-full items-center gap-3 px-4 py-4 transition-colors hover:bg-white/[0.04]"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
            <Users className="h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('organiser.collaborators.title')}</span>
          {allLoading ? (
            <Skeleton className="h-5 w-6 rounded-full" />
          ) : (
            collaboratorCount > 0 && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">
                {collaboratorCount}
              </span>
            )
          )}
          <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
        </Link>
      </div>

      <div className="overflow-hidden rounded-2xl border border-red-500/15 bg-white/5">
        <button
          onClick={openDelete}
          className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-white/[0.04]"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500/10">
            <Trash2 className="h-4 w-4 text-red-400" />
          </div>
          <span className="flex-1 text-sm font-semibold text-red-400">
            {t('organiser.org.deleteButton')}
          </span>
        </button>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        tone="destructive"
        icon={Trash2}
        title={t('organiser.org.deleteTitle')}
        description={t('organiser.org.deleteDesc')}
        irreversible
        confirmLabel={t('organiser.org.deleteConfirm')}
        isLoading={deleteOrg.isPending}
        countdownSeconds={5}
        onConfirm={() => deleteOrg.mutate()}
      />
    </div>
  )
}
