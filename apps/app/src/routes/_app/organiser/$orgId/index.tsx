import { createFileRoute, Link } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { CalendarDays, ChevronRight, Trash2, Users } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { Skeleton } from '@/components/ui/skeleton'
import { useDeleteOrganisation } from '@/features/organiser/hooks/useDeleteOrganisation'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'
import { useOrgMembers } from '@/features/organiser/hooks/useOrgMembers'

export const Route = createFileRoute('/_app/organiser/$orgId/')({
  component: OrgDashboardPage,
})

const COUNTDOWN = 5

function OrgDashboardPage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()

  const { data: orgsData, isLoading: orgLoading } = useMyOrganisations()
  const org = orgsData?.items.find((o) => o.id === orgId)

  const { data: membersData, isLoading: membersLoading } = useOrgMembers(orgId)
  const { data: eventsData, isLoading: eventsLoading } = useOrgEvents(orgId)

  const allLoading = orgLoading || eventsLoading || membersLoading
  const memberCount = membersData?.length ?? 0
  const eventCount = eventsData?.items.length ?? 0

  const [deleteOpen, setDeleteOpen] = useState(false)
  const [seconds, setSeconds] = useState(COUNTDOWN)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const deleteOrg = useDeleteOrganisation()

  const openDelete = () => {
    setSeconds(COUNTDOWN)
    setDeleteOpen(true)
  }

  const closeDelete = () => {
    setDeleteOpen(false)
    if (timerRef.current) clearInterval(timerRef.current)
  }

  useEffect(() => {
    if (!deleteOpen) return
    timerRef.current = setInterval(() => {
      setSeconds((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current!)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [deleteOpen])

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/organiser" />
      <div>
        {allLoading ? (
          <Skeleton className="h-8 w-40" />
        ) : (
          <h1 className="text-2xl font-semibold">{org?.name}</h1>
        )}
        {org?.slug && <p className="text-muted-foreground text-sm">@{org.slug}</p>}
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <Link
          to="/organiser/$orgId/events"
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
          to="/organiser/$orgId/members"
          params={{ orgId }}
          className="flex w-full items-center gap-3 px-4 py-4 transition-colors hover:bg-white/[0.04]"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
            <Users className="h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('organiser.members.title')}</span>
          {allLoading ? (
            <Skeleton className="h-5 w-6 rounded-full" />
          ) : (
            memberCount > 0 && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">
                {memberCount}
              </span>
            )
          )}
          <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
        </Link>
      </div>

      {/* Danger zone */}
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

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {deleteOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && closeDelete()}
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
                  <Trash2 className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-red-400">
                    {t('organiser.org.deleteTitle')}
                  </h3>
                  <p className="text-muted-foreground text-xs capitalize">{org?.name ?? ''}</p>
                </div>
              </div>
              <p className="text-muted-foreground mb-6 text-sm whitespace-pre-line">
                {t('organiser.org.deleteDesc')}
              </p>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                  onClick={closeDelete}
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => deleteOrg.mutate(orgId)}
                  disabled={seconds > 0 || deleteOrg.isPending}
                  className="flex h-10 min-w-[120px] items-center justify-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {deleteOrg.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : seconds > 0 ? (
                    `Wait ${seconds}s`
                  ) : (
                    <>
                      <Trash2 className="h-3.5 w-3.5" />
                      {t('common.delete')}
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
