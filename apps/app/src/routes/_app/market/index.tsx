import { createFileRoute, Link } from '@tanstack/react-router'
import { ChevronRight, Clock, Tag, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Skeleton } from '@/components/ui/skeleton'
import { usePendingMarketAssignment } from '@/features/market/hooks/useMarketAssignment'
import { useMyQueues } from '@/features/market/hooks/useMyQueues'
import { useTickets } from '@/features/tickets/hooks/useTickets'

export const Route = createFileRoute('/_app/market/')({
  component: MarketPage,
})

function MarketPage() {
  const { t } = useTranslation()
  const { data: assignment, isLoading: assignmentLoading } = usePendingMarketAssignment()
  const { data: tickets, isLoading: ticketsLoading } = useTickets()
  const { data: queues, isLoading: queuesLoading } = useMyQueues()

  const badgesLoading = assignmentLoading || ticketsLoading || queuesLoading
  const listedCount = (tickets ?? []).filter((t) => t.state === 'on_sale').length
  const waitlistCount = queues?.length ?? 0
  const claimsCount = assignment ? 1 : 0

  const sections = [
    {
      to: '/market/my-listings' as const,
      icon: Tag,
      label: t('market.myTicketsOnSale'),
      count: listedCount,
    },
    {
      to: '/market/claims' as const,
      icon: Clock,
      label: t('market.myTicketsToClaim'),
      count: claimsCount,
    },
    {
      to: '/market/waitlists' as const,
      icon: Users,
      label: t('market.myWaitlists'),
      count: waitlistCount,
    },
  ]

  return (
    <div className="mx-auto min-h-screen max-w-[430px] px-4 pt-5 pb-28 space-y-6">
      <h1 className="text-2xl font-bold">{t('market.title')}</h1>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        {sections.map((s, i) => {
          const Icon = s.icon
          return (
            <Link
              key={s.to}
              to={s.to}
              className={`flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5 ${i > 0 ? 'border-t border-white/10' : ''}`}
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/8">
                <Icon className="h-4 w-4 text-white/60" />
              </div>
              <span className="flex-1 text-sm font-medium">{s.label}</span>
              {badgesLoading ? (
                <Skeleton className="h-5 w-6 rounded-full" />
              ) : s.count > 0 ? (
                <span className="bg-white/10 text-white/60 rounded-full px-2 py-0.5 text-xs">
                  {s.count}
                </span>
              ) : null}
              <ChevronRight className="h-4 w-4 text-white/30" />
            </Link>
          )
        })}
      </div>

    </div>
  )
}
