import { createFileRoute, Link } from '@tanstack/react-router'
import { ChevronRight, FileText, Shield, Tag } from 'lucide-react'
import { type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'

export const Route = createFileRoute('/_app/profile/about')({
  component: AboutPage,
})

const APP_VERSION = '0.1.0'

function StaticRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
        {icon}
      </div>
      <span className="flex-1 text-sm font-medium">{label}</span>
      <span className="text-muted-foreground text-sm">{value}</span>
    </div>
  )
}

function LinkRow({ icon, label, to }: { icon: ReactNode; label: string; to: string }) {
  return (
    <Link to={to} className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
        {icon}
      </div>
      <span className="flex-1 text-sm font-medium">{label}</span>
      <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
    </Link>
  )
}

function AboutPage() {
  const { t } = useTranslation()
  const iconClass = 'h-4 w-4 text-muted-foreground'

  return (
    <div className="min-h-screen px-4 pt-4 pb-28">
      <BackButton to="/profile" className="mb-6" />
      <h1 className="mb-6 text-xl font-bold">{t('profile.about.title')}</h1>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <StaticRow
          icon={<Tag className={iconClass} />}
          label={t('profile.about.version')}
          value={APP_VERSION}
        />
      </div>

      <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <LinkRow
          icon={<FileText className={iconClass} />}
          label={t('profile.about.terms')}
          to="/profile/terms"
        />

        <div className="mx-4 border-t border-white/10" />

        <LinkRow
          icon={<Shield className={iconClass} />}
          label={t('profile.about.privacy')}
          to="/profile/privacy"
        />
      </div>
    </div>
  )
}
