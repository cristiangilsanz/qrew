import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { scannerApi } from '@/features/scanner/api'
import { queryKeys } from '@/lib/queryKeys'

export const Route = createFileRoute('/_app/management/$orgId/events/$eventId/stats')({
  component: EntryStatsPage,
})

function StatCardSkeleton() {
  return (
    <div className="px-4 py-5 text-center">
      <div className="mx-auto mb-2 h-8 w-10 animate-pulse rounded-md bg-white/10" />
      <div className="mx-auto h-3 w-14 animate-pulse rounded bg-white/10" />
    </div>
  )
}

function EntryStatsPage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()

  const { data: stats, isLoading } = useQuery({
    queryKey: queryKeys.entryStats.detail(eventId),
    queryFn: () => scannerApi.getEntryStats(eventId),
    refetchInterval: 30_000,
  })

  const entryRate =
    stats && stats.total_issued > 0
      ? Math.round((stats.total_entered / stats.total_issued) * 100)
      : 0

  return (
    <div className="pb-28">
      <div className="sticky top-0 z-10 bg-[hsl(0,0%,10%)] px-4 py-4">
        <BackButton to="/management/$orgId/events/$eventId" params={{ orgId, eventId }} />
        <h1 className="mt-2 text-2xl font-semibold">{t('organiser.entryStats.title')}</h1>
      </div>

      <div className="mx-auto max-w-2xl space-y-4 px-4 pt-4">
        {/* Issued, Entered, Remaining */}
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          <div className="grid grid-cols-3 divide-x divide-white/10">
            {isLoading ? (
              <>
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
              </>
            ) : (
              <>
                <div className="px-4 py-5 text-center">
                  <p className="text-2xl font-bold">{stats?.total_issued ?? 0}</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {t('organiser.entryStats.totalIssued')}
                  </p>
                </div>
                <div className="px-4 py-5 text-center">
                  <p className="text-2xl font-bold text-green-400">{stats?.total_entered ?? 0}</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {t('organiser.entryStats.totalEntered')}
                  </p>
                </div>
                <div className="px-4 py-5 text-center">
                  <p className="text-2xl font-bold">{stats?.total_remaining ?? 0}</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {t('organiser.entryStats.totalRemaining')}
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Entry rate progress bar */}
          <div className="border-t border-white/10 px-4 py-3">
            {isLoading ? (
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <div className="h-3 w-20 animate-pulse rounded bg-white/10" />
                  <div className="h-3 w-8 animate-pulse rounded bg-white/10" />
                </div>
                <div className="h-1.5 w-full animate-pulse rounded-full bg-white/10" />
              </div>
            ) : (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-muted-foreground text-xs">
                    {t('organiser.entryStats.entryRate')}
                  </p>
                  <p className="text-xs font-medium">{entryRate}%</p>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-green-500 transition-all duration-500"
                    style={{ width: `${entryRate}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Last scan */}
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
          {isLoading ? (
            <div className="flex items-center justify-between">
              <div className="h-3 w-16 animate-pulse rounded bg-white/10" />
              <div className="h-3 w-24 animate-pulse rounded bg-white/10" />
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <p className="text-muted-foreground text-xs">{t('organiser.entryStats.lastScan')}</p>
              <p className="text-xs font-medium">
                {stats?.last_scan_at
                  ? new Date(stats.last_scan_at).toLocaleTimeString()
                  : t('organiser.entryStats.noScans')}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
