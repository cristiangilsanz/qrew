import { Link } from '@tanstack/react-router'
import { Compass, Home, Ticket, User } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '@/lib/utils'

const tabs = [
  { to: '/home' as const, icon: Home, labelKey: 'nav.home' },
  { to: '/events' as const, icon: Compass, labelKey: 'nav.discover' },
  { to: '/tickets' as const, icon: Ticket, labelKey: 'nav.tickets' },
  { to: '/profile' as const, icon: User, labelKey: 'nav.profile' },
]

export function BottomDock() {
  const { t } = useTranslation()

  return (
    <nav className="bg-background/80 fixed bottom-0 left-1/2 z-50 w-full max-w-[430px] -translate-x-1/2 border-t backdrop-blur-md">
      <div className="flex items-center">
        {tabs.map(({ to, icon: Icon, labelKey }) => (
          <Link
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex flex-1 flex-col items-center justify-center gap-1 rounded-xl py-2 transition-colors',
                isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
              )
            }
          >
            <Icon className="h-5 w-5" strokeWidth={1.75} />
            <span className="text-center text-[10px] font-medium leading-none tracking-wide">{t(labelKey)}</span>
          </Link>
        ))}
      </div>
    </nav>
  )
}
