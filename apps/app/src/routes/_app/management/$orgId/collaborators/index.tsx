// implements members
import { createFileRoute, Link } from '@tanstack/react-router'
import { Search, Trash2, UserMinus, UserPlus, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyMessage } from '@/components/ui/empty-message'
import { FloatingActions } from '@/components/ui/floating-actions'
import { PageError } from '@/components/ui/page-error'
import {
  SEARCH_CLEAR_CLASS,
  SEARCH_ICON_CLASS,
  SEARCH_INPUT_CLASS,
} from '@/components/ui/search-field'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useOrgCollaborators } from '@/features/organiser/hooks/useOrgCollaborators'
import { useRemoveCollaborator } from '@/features/organiser/hooks/useRemoveCollaborator'
import { useUserPublicProfiles } from '@/features/profile/hooks/useUserPublicProfiles'
import { formatDate } from '@/lib/formatDate'

export const Route = createFileRoute('/_app/management/$orgId/collaborators/')({
  component: OrgMembersPage,
})

// renders the org members page component
function OrgMembersPage() {
  const { t, i18n } = useTranslation()
  const { orgId } = Route.useParams()
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const {
    data: members,
    isLoading: collaboratorsLoading,
    isError: collaboratorsError,
    refetch: refetchCollaborators,
  } = useOrgCollaborators(orgId)
  // implements member ids
  const memberIds = (members ?? []).map((m) => m.user_id)
  const { data: profiles, isLoading: profilesLoading } = useUserPublicProfiles(memberIds)
  const profileById = Object.fromEntries((profiles ?? []).map((p) => [p.id, p]))
  const isLoading = collaboratorsLoading || profilesLoading

  const visibleCollaborators = query.trim()
    ? (members ?? []).filter((m) => {
        const p = profileById[m.user_id]
        if (!p) return false
        const q = query.toLowerCase()
        return p.full_name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q)
      })
    : (members ?? [])

  const remove = useRemoveCollaborator(orgId)

  if (collaboratorsError) return <PageError onRetry={() => void refetchCollaborators()} />

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/management/$orgId" params={{ orgId }} />
      <h1 className="text-2xl font-semibold">{t('organiser.collaborators.title')}</h1>

      <div className="relative">
        <Search className={SEARCH_ICON_CLASS} />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('organiser.collaborators.searchPlaceholder')}
          className={SEARCH_INPUT_CLASS}
        />
        {query && (
          <button type="button" onClick={() => setQuery('')} className={SEARCH_CLEAR_CLASS}>
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {isLoading && (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          {[0, 1, 2].map((i) => (
            <div key={i}>
              {i > 0 && <div className="mx-4 border-t border-white/10" />}
              <div className="flex items-center gap-3 px-4 py-4">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-44" />
                </div>
                <Skeleton className="h-5 w-18 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && members && !collaboratorsError && visibleCollaborators.length === 0 && (
        <EmptyMessage>{t('organiser.collaborators.empty')}</EmptyMessage>
      )}

      {!isLoading && members && visibleCollaborators.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          {visibleCollaborators.map((m, i) => (
            <div key={m.user_id}>
              {i > 0 && <div className="border-t border-white/10" />}
              <div className="flex items-center gap-3 px-4 py-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold uppercase">
                  {(profileById[m.user_id]?.full_name ?? '?').slice(0, 2)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {profileById[m.user_id]?.full_name ?? ''}
                  </p>
                  <p className="text-muted-foreground truncate text-xs">
                    {profileById[m.user_id]?.email ?? ''}
                  </p>
                  <p className="text-muted-foreground mt-0.5 text-xs">
                    {t('organiser.collaborators.joined')}{' '}
                    {formatDate(m.joined_at, i18n.language, {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })}
                  </p>
                </div>
                <StatusChip label={m.role} />
                <button
                  onClick={() => setConfirmDelete(m.user_id)}
                  className="shrink-0 rounded-lg p-1.5 text-white/30 transition-colors hover:bg-red-500/10 hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={confirmDelete !== null}
        onOpenChange={(next) => !next && setConfirmDelete(null)}
        tone="destructive"
        icon={UserMinus}
        title={t('organiser.collaborators.removeTitle')}
        description={t('organiser.collaborators.removeConfirmDesc')}
        irreversible
        confirmLabel={t('organiser.collaborators.removeConfirm')}
        isLoading={remove.isPending}
        onConfirm={() => confirmDelete && remove.mutate(confirmDelete)}
      />

      <FloatingActions>
        <Link
          to="/management/$orgId/collaborators/new"
          params={{ orgId }}
          className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        >
          <UserPlus className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">{t('organiser.collaborators.addMember')}</span>
        </Link>
      </FloatingActions>
    </div>
  )
}
