import { createFileRoute,Link } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { Search, Trash2, UserMinus, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useOrgMembers } from '@/features/organiser/hooks/useOrgMembers'
import { useRemoveMember } from '@/features/organiser/hooks/useRemoveMember'
import { useUserPublicProfiles } from '@/features/profile/hooks/useUserPublicProfiles'

export const Route = createFileRoute('/_app/organiser/$orgId/members/')({
  component: OrgMembersPage,
})



function OrgMembersPage() {
  const { t, i18n } = useTranslation()
  const { orgId } = Route.useParams()
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const { data: members, isLoading: membersLoading } = useOrgMembers(orgId)
  const memberIds = (members ?? []).map((m) => m.user_id)
  const { data: profiles, isLoading: profilesLoading } = useUserPublicProfiles(memberIds)
  const profileById = Object.fromEntries((profiles ?? []).map((p) => [p.id, p]))
  const isLoading = membersLoading || profilesLoading

  const visibleMembers = query.trim()
    ? (members ?? []).filter((m) => {
        const p = profileById[m.user_id]
        if (!p) return false
        const q = query.toLowerCase()
        return p.full_name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q)
      })
    : (members ?? [])

  const remove = useRemoveMember(orgId)

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/organiser/$orgId" params={{ orgId }} />
      <h1 className="text-2xl font-semibold">{t('organiser.members.title')}</h1>

        <div className="relative">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('organiser.members.searchPlaceholder')}
            className="border-white/15 bg-white/5 placeholder:text-muted-foreground focus:border-primary/60 w-full rounded-2xl border py-3 pr-4 pl-9 text-sm outline-none transition-colors"
          />
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
          {visibleMembers.length === 0 && (
            <p className="text-muted-foreground py-8 text-center text-sm">
              {t('organiser.members.empty')}
            </p>
          )}
          {visibleMembers.map((m, i) => (
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
                    {t('organiser.members.joined')}{' '}
                    {new Date(m.joined_at).toLocaleDateString(i18n.language, {
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

      {/* Delete member modal */}
      <AnimatePresence>
        {confirmDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setConfirmDelete(null)}
          >
            <motion.div
              initial={{ y: 32, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 32, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <UserMinus className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-red-400">
                    {t('organiser.members.removeTitle')}
                  </h3>
                  <p className="text-muted-foreground text-xs">
                    {profileById[confirmDelete]?.full_name ?? '—'}
                  </p>
                </div>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">
                {t('organiser.members.removeConfirmDesc')}
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
                  {remove.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <UserMinus className="h-3.5 w-3.5" />
                  )}
                  {t('organiser.members.removeConfirm')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB */}
      <Link
        to="/organiser/$orgId/members/new"
        params={{ orgId }}
        className="bg-primary hover:bg-primary/90 fixed bottom-24 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        style={{ right: 'max(calc((100vw - 430px) / 2 + 1.5rem), 1.5rem)' }}
      >
        <UserPlus className="h-5 w-5 shrink-0" />
        <span className="text-sm font-semibold">{t('organiser.members.addMember')}</span>
      </Link>
    </div>
  )
}
