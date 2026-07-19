import { Link, useRouterState } from '@tanstack/react-router'
import type { LucideIcon } from 'lucide-react'
import { Building2, Compass, Home, Ticket, User } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '@/lib/utils'
import { useProfile } from '@/features/profile/hooks/useProfile'
import { useReservedTicketsCount } from '@/features/tickets/hooks/useReservedTicketsCount'

const baseTabs = [
  { to: '/home' as const, icon: Home, labelKey: 'nav.home' },
  { to: '/events' as const, icon: Compass, labelKey: 'nav.discover' },
  { to: '/tickets' as const, icon: Ticket, labelKey: 'nav.tickets' },
  { to: '/profile' as const, icon: User, labelKey: 'nav.profile' },
]

const organiserTab = { to: '/organiser' as const, icon: Building2, labelKey: 'nav.organiser' }

function DockTab({
  to,
  icon: Icon,
  labelKey,
  badge,
}: {
  to: string
  icon: LucideIcon
  labelKey: string
  badge?: number
}) {
  const { t } = useTranslation()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const isActive = pathname.startsWith(to)

  return (
    <Link
      to={to}
      className={cn(
        'relative flex h-16 flex-1 flex-col items-center justify-center gap-1 transition-colors',
        isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      <span
        className={cn(
          'absolute top-0 h-0.5 w-8 rounded-full transition-all duration-300',
          isActive ? 'bg-primary shadow-[0_0_8px_hsl(var(--primary))]' : 'bg-transparent',
        )}
      />
      <span className="relative">
        <Icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
        {badge != null && badge > 0 && (
          <span className="absolute -top-1.5 -right-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-yellow-500 px-1 text-[9px] leading-none font-bold text-black">
            {badge > 9 ? '9+' : badge}
          </span>
        )}
      </span>
      <span className="mt-1 text-[10px] leading-none font-medium">{t(labelKey)}</span>
    </Link>
  )
}

export function BottomDock() {
  const { data: profile } = useProfile()
  const reservedCount = useReservedTicketsCount()

  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-white/25 bg-black/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-[430px]">
        {baseTabs.map((tab) => (
          <DockTab
            key={tab.to}
            {...tab}
            badge={tab.to === '/tickets' ? reservedCount : undefined}
          />
        ))}
        {profile?.is_admin && <DockTab {...organiserTab} />}
      </div>
    </nav>
  )
}
