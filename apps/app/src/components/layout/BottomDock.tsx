import { Link, useRouterState } from '@tanstack/react-router'
import type { LucideIcon } from 'lucide-react'
import { Compass, Home, Ticket, User } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '@/lib/utils'

const tabs = [
  { to: '/home' as const, icon: Home, labelKey: 'nav.home' },
  { to: '/events' as const, icon: Compass, labelKey: 'nav.discover' },
  { to: '/tickets' as const, icon: Ticket, labelKey: 'nav.tickets' },
  { to: '/profile' as const, icon: User, labelKey: 'nav.profile' },
]

function DockTab({
  to,
  icon: Icon,
  labelKey,
}: {
  to: string
  icon: LucideIcon
  labelKey: string
}) {
  const { t } = useTranslation()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const isActive = pathname.startsWith(to)

  return (
    <Link
      to={to}
      className={cn(
        'flex h-16 flex-1 flex-col items-center justify-center gap-1 transition-colors',
        isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      <span
        className={cn(
          'mb-1 h-0.5 w-8 rounded-full transition-all duration-300',
          isActive ? 'bg-primary shadow-[0_0_8px_hsl(var(--primary))]' : 'bg-transparent',
        )}
      />
      <Icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
      <span className="mt-1 text-[10px] font-medium leading-none">{t(labelKey)}</span>
    </Link>
  )
}

export function BottomDock() {
  return (
    <nav className="bg-background/90 fixed inset-x-0 bottom-0 z-50 backdrop-blur-md">
      <div className="mx-auto flex max-w-[430px]">
        {tabs.map((tab) => (
          <DockTab key={tab.to} {...tab} />
        ))}
      </div>
    </nav>
  )
}
