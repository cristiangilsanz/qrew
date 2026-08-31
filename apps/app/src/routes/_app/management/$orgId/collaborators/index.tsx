// implements members
import { createFileRoute, Link } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { Search, Trash2, UserMinus, UserPlus, X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
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

      {!isLoading && members && (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          {!collaboratorsError && visibleCollaborators.length === 0 && (
            <p className="text-muted-foreground py-8 text-center text-sm">
              {t('organiser.collaborators.empty')}
            </p>
          )}
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

      <AnimatePresence>
        {confirmDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[200] flex items-center justify-center p-4"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setConfirmDelete(null)}
          >
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <UserMinus className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-red-400">
                    {t('organiser.collaborators.removeTitle')}
                  </h3>
                  <p className="text-muted-foreground text-xs">
                    {profileById[confirmDelete]?.full_name ?? '—'}
                  </p>
                </div>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">
                {t('organiser.collaborators.removeConfirmDesc')}
              </p>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                  onClick={() => setConfirmDelete(null)}
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => {
                    remove.mutate(confirmDelete)
                    setConfirmDelete(null)
                  }}
                  disabled={remove.isPending}
                  className="flex h-10 items-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  <UserMinus className="h-3.5 w-3.5" />
                  {t('organiser.collaborators.removeConfirm')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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
