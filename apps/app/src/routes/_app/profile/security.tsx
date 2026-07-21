import { createFileRoute } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronDown,
  ChevronRight,
  ClockArrowUp,
  KeyRound,
  Lock,
  Monitor,
  Smartphone,
  Trash2,
} from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { PasskeyList } from '@/features/passkeys/components/PasskeyList'
import { ChangePasswordForm } from '@/features/profile/components/ChangePasswordForm'
import { SessionList } from '@/features/profile/components/SessionList'
import { useAuditLog } from '@/features/profile/hooks/useAuditLog'
import {
  useDevices,
  useRevokeAllDevices,
  useRevokeDevice,
} from '@/features/profile/hooks/useDevices'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/profile/security')({
  component: SecurityPage,
})

type ExpandedRow = 'password' | 'passkeys' | 'sessions' | 'devices' | 'activity' | null

const expandVariants = {
  hidden: { height: 0, opacity: 0 },
  visible: { height: 'auto', opacity: 1, transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] } },
  exit: { height: 0, opacity: 0, transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] } },
}

function ExpandRow({
  id,
  icon,
  label,
  expanded,
  onToggle,
  children,
}: {
  id: ExpandedRow
  icon: ReactNode
  label: string
  expanded: ExpandedRow
  onToggle: (row: ExpandedRow) => void
  children: ReactNode
}) {
  const isOpen = expanded === id
  return (
    <>
      <button
        onClick={() => onToggle(id)}
        className="flex w-full items-center gap-3 px-4 py-4 text-left"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
          {icon}
        </div>
        <span className="flex-1 text-sm font-medium">{label}</span>
        <ChevronRight
          className={cn(
            'text-muted-foreground h-4 w-4 shrink-0 transition-transform duration-200',
            isOpen && 'text-primary rotate-90',
          )}
        />
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key={id}
            variants={expandVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{ overflow: 'hidden' }}
          >
            <div className="border-t border-white/10 bg-white/[0.03] px-4 pt-4 pb-4">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function DeviceList() {
  const { t, i18n } = useTranslation()
  const { data, isLoading } = useDevices()
  const revoke = useRevokeDevice()
  const revokeAll = useRevokeAllDevices()

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="border-primary h-6 w-6 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  const devices = data?.items ?? []

  return (
    <div className="space-y-2">
      {devices.length === 0 && (
        <p className="text-muted-foreground py-4 text-center text-sm">
          {t('profile.security.noDevices')}
        </p>
      )}
      <ul className="space-y-1">
        {devices.map((device) => (
          <li
            key={device.id}
            className="flex items-center gap-3 rounded-xl bg-white/[0.04] px-3 py-3"
          >
            <Smartphone className="text-muted-foreground h-4 w-4 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white/80">{device.name}</p>
              {device.last_seen_at && (
                <p className="text-muted-foreground text-xs">
                  Last seen {new Date(device.last_seen_at).toLocaleDateString(i18n.language)}
                </p>
              )}
            </div>
            <button
              onClick={() => revoke.mutate(device.id)}
              disabled={revoke.isPending}
              className="text-muted-foreground hover:text-destructive shrink-0 disabled:opacity-40"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
      {devices.length > 1 && (
        <div className="flex justify-end pt-1">
          <button
            onClick={() => revokeAll.mutate()}
            disabled={revokeAll.isPending}
            className="bg-destructive flex h-9 items-center gap-2 rounded-full px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t('profile.security.revokeAll')}
          </button>
        </div>
      )}
    </div>
  )
}

const PAGE = 5

function AuditLog() {
  const { t, i18n } = useTranslation()
  const { data, isLoading } = useAuditLog()
  const [visible, setVisible] = useState(PAGE)

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="border-primary h-6 w-6 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  const events = data?.items ?? []
  const shown = events.slice(0, visible)
  const hasMore = visible < events.length

  if (events.length === 0) {
    return (
      <p className="text-muted-foreground py-4 text-center text-sm">
        {t('profile.security.noActivity')}
      </p>
    )
  }

  return (
    <div>
      <div className="relative">
        <div className="absolute top-2 bottom-2 left-[5px] w-px bg-white/10" />
        <div className="space-y-5">
          {shown.map((event) => (
            <div key={event.id} className="relative flex items-start gap-3">
              <div className="bg-primary relative z-10 mt-1 h-[11px] w-[11px] shrink-0 rounded-full" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white/80">{event.summary}</p>
                <p className="text-muted-foreground mt-0.5 text-xs">
                  {new Date(event.created_at).toLocaleString(i18n.language, {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  {event.ip_address && ` · ${event.ip_address}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
      {hasMore && (
        <button
          onClick={() => setVisible((v) => v + PAGE)}
          className="bg-primary mt-4 flex h-9 w-full items-center justify-center gap-2 rounded-full text-sm font-semibold text-white disabled:opacity-50"
        >
          <ChevronDown className="h-3.5 w-3.5" />
          {t('profile.security.showMore')}
        </button>
      )}
    </div>
  )
}

function SecurityPage() {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState<ExpandedRow>(null)

  const toggle = (row: ExpandedRow) => setExpanded((prev) => (prev === row ? null : row))

  const iconClass = 'h-4 w-4 text-muted-foreground'

  return (
    <div className="min-h-screen px-4 pt-4 pb-28">
      <BackButton to="/profile" className="mb-6" />
      <h1 className="mb-6 text-xl font-bold">{t('profile.security.title')}</h1>

      <p className="text-muted-foreground mb-3 px-1 text-xs font-semibold tracking-wider uppercase">
        {t('profile.security.authSection')}
      </p>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <ExpandRow
          id="password"
          icon={<Lock className={iconClass} />}
          label={t('profile.security.passwordLabel')}
          expanded={expanded}
          onToggle={toggle}
        >
          <ChangePasswordForm hideTitle />
        </ExpandRow>

        <div className="mx-4 border-t border-white/10" />

        <ExpandRow
          id="passkeys"
          icon={<KeyRound className={iconClass} />}
          label={t('profile.security.passkeysLabel')}
          expanded={expanded}
          onToggle={toggle}
        >
          <PasskeyList />
        </ExpandRow>
      </div>

      <p className="text-muted-foreground mt-6 mb-3 px-1 text-xs font-semibold tracking-wider uppercase">
        {t('profile.security.sessionsSection')}
      </p>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <ExpandRow
          id="sessions"
          icon={<Monitor className={iconClass} />}
          label={t('profile.security.activeSessionsLabel')}
          expanded={expanded}
          onToggle={toggle}
        >
          <SessionList />
        </ExpandRow>

        <div className="mx-4 border-t border-white/10" />

        <ExpandRow
          id="devices"
          icon={<Smartphone className={iconClass} />}
          label={t('profile.security.trustedDevicesLabel')}
          expanded={expanded}
          onToggle={toggle}
        >
          <DeviceList />
        </ExpandRow>
      </div>

      <p className="text-muted-foreground mt-6 mb-3 px-1 text-xs font-semibold tracking-wider uppercase">
        {t('profile.security.activitySection')}
      </p>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <ExpandRow
          id="activity"
          icon={<ClockArrowUp className={iconClass} />}
          label={t('profile.security.recentActivityLabel')}
          expanded={expanded}
          onToggle={toggle}
        >
          <AuditLog />
        </ExpandRow>
      </div>
    </div>
  )
}
