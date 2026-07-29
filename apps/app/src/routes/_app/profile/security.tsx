import { createFileRoute } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronDown,
  ChevronRight,
  ClockArrowUp,
  Copy,
  ExternalLink,
  Info,
  KeyRound,
  Lock,
  Monitor,
  RefreshCw,
  Shield,
  ShieldCheck,
  ShieldOff,
  Smartphone,
  Trash2,
} from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { totpApi } from '@/features/auth/api'

import { BackButton } from '@/components/ui/back-button'
import { Button } from '@/components/ui/button'
import { StatusChip } from '@/components/ui/status-chip'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { PasskeyList } from '@/features/passkeys/components/PasskeyList'
import { ChangePasswordForm } from '@/features/profile/components/ChangePasswordForm'
import { SessionList } from '@/features/profile/components/SessionList'
import { useAuditLog } from '@/features/profile/hooks/useAuditLog'
import {
  useDevices,
  useRevokeAllDevices,
  useRevokeDevice,
} from '@/features/profile/hooks/useDevices'
import { formatDate, formatDateTime } from '@/lib/formatDate'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/profile/security')({
  component: SecurityPage,
})

type ExpandedRow = 'password' | 'totp' | 'passkeys' | 'sessions' | 'devices' | 'activity' | null

const expandVariants = {
  hidden: { height: 0, opacity: 0 },
  visible: { height: 'auto', opacity: 1, transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] } },
  exit: { height: 0, opacity: 0, transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] } },
}

function ExpandRow({
  id,
  icon,
  label,
  badge,
  expanded,
  onToggle,
  children,
}: {
  id: ExpandedRow
  icon: ReactNode
  label: string
  badge?: ReactNode
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
        {badge}
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
  const [confirmDeviceId, setConfirmDeviceId] = useState<string | null>(null)
  const [confirmRevokeAll, setConfirmRevokeAll] = useState(false)

  if (isLoading) {
    return (
      <div className="space-y-1">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center gap-3 rounded-xl bg-white/[0.04] px-3 py-3">
            <Skeleton className="h-4 w-4 rounded" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-4 w-4 rounded" />
          </div>
        ))}
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
                  Last seen {formatDate(device.last_seen_at, i18n.language)}
                </p>
              )}
            </div>
            <button
              onClick={() => setConfirmDeviceId(device.id)}
              disabled={revoke.isPending}
              className="text-muted-foreground hover:text-destructive shrink-0 disabled:opacity-40"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            {confirmDeviceId === device.id && (
              <ConfirmDialog
                open
                onOpenChange={(o) => !o && setConfirmDeviceId(null)}
                title={
                  device.is_current
                    ? t('profile.security.revokeCurrentDeviceTitle')
                    : t('profile.security.revokeDeviceTitle')
                }
                description={
                  device.is_current
                    ? t('profile.security.revokeCurrentDeviceDesc')
                    : t('profile.security.revokeDeviceDesc')
                }
                confirmLabel={
                  device.is_current
                    ? t('profile.security.revokeAndSignOut')
                    : t('profile.security.removeDevice')
                }
                destructive
                isLoading={revoke.isPending}
                onConfirm={() => revoke.mutate({ deviceId: device.id, isCurrent: device.is_current })}
              />
            )}
          </li>
        ))}
      </ul>
      {devices.length > 1 && (
        <div className="flex justify-end pt-1">
          <button
            onClick={() => setConfirmRevokeAll(true)}
            disabled={revokeAll.isPending}
            className="bg-destructive flex h-9 items-center gap-2 rounded-full px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t('profile.security.revokeAll')}
          </button>
          <ConfirmDialog
            open={confirmRevokeAll}
            onOpenChange={setConfirmRevokeAll}
            title={t('profile.security.revokeAllDevicesTitle')}
            description={t('profile.security.revokeAllDevicesDesc')}
            confirmLabel={t('profile.security.revokeAndSignOut')}
            destructive
            isLoading={revokeAll.isPending}
            onConfirm={() => revokeAll.mutate()}
          />
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
      <div className="space-y-5">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-start gap-3">
            <Skeleton className="mt-1 h-[11px] w-[11px] rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        ))}
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
                  {formatDateTime(event.created_at, i18n.language, {
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

type TotpStep = 'status' | 'setup' | 'confirm' | 'backup' | 'disable'

function TotpSection() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [step, setStep] = useState<TotpStep>('status')
  const [pendingSecret, setPendingSecret] = useState('')
  const [pendingUri, setPendingUri] = useState('')
  const [pendingBackups, setPendingBackups] = useState<string[]>([])
  const [confirmCode, setConfirmCode] = useState('')
  const [disableCode, setDisableCode] = useState('')

  const { data: status, isLoading } = useQuery({
    queryKey: ['totp', 'status'],
    queryFn: () => totpApi.status(),
  })

  const setupMut = useMutation({
    mutationFn: () => totpApi.setup(),
    onSuccess: (data) => {
      setPendingSecret(data.secret)
      setPendingUri(data.provisioning_uri)
      setPendingBackups(data.backup_codes)
      setStep('setup')
    },
  })

  const confirmMut = useMutation({
    mutationFn: () => totpApi.confirm(pendingSecret, confirmCode, pendingBackups),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['totp', 'status'] })
      setStep('backup')
    },
    onError: () => toast.error(t('auth.totp.invalidCode')),
  })

  const disableMut = useMutation({
    mutationFn: () => totpApi.disable(disableCode),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['totp', 'status'] })
      setStep('status')
      setDisableCode('')
      toast.success(t('profile.security.totp.disabledToast'))
    },
    onError: () => toast.error(t('auth.totp.invalidCode')),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-1">
        <Skeleton className="h-9 w-24 rounded-full" />
      </div>
    )
  }

  const enabled = status?.enabled ?? false

  if (step === 'status') {
    return (
      <div className="flex justify-center">
        {enabled ? (
          <button
            onClick={() => setStep('disable')}
            className="flex items-center gap-2 rounded-full border border-red-500/30 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:border-red-500/60"
          >
            <ShieldOff className="h-4 w-4" />
            {t('profile.security.totp.disable')}
          </button>
        ) : (
          <Button
            onClick={() => setupMut.mutate()}
            disabled={setupMut.isPending}
            className="rounded-full"
          >
            <ShieldCheck className="h-4 w-4" />
            {t('profile.security.totp.setUp')}
          </Button>
        )}
      </div>
    )
  }

  if (step === 'setup') {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground text-sm">{t('profile.security.totp.scanInstruction')}</p>
        <div className="flex justify-center">
          <div className="rounded-xl bg-white p-3">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(pendingUri)}`}
              alt="TOTP QR code"
              className="h-[180px] w-[180px] block"
            />
          </div>
        </div>
        <div className="flex justify-end">
          <a
            href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-white/70 flex items-center gap-1.5 text-xs transition-colors"
          >
            <Info className="h-3.5 w-3.5 shrink-0" />
            <span>{t('profile.security.totp.getAuthApp')}</span>
            <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        </div>
        <div>
          <p className="mb-1 text-xs text-white/50">{t('profile.security.totp.manualKey')}</p>
          <button
            onClick={() => { void navigator.clipboard.writeText(pendingSecret); toast.success(t('common.copied')) }}
            className="flex w-full items-center gap-2 rounded-lg bg-white/5 px-3 py-2 font-mono text-xs text-white/80"
          >
            <Copy className="h-3 w-3 shrink-0" />
            <span className="truncate">{pendingSecret}</span>
          </button>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">{t('profile.security.totp.confirmCode')}</label>
          <input
            type="text"
            inputMode="numeric"
            maxLength={10}
            value={confirmCode}
            onChange={(e) => setConfirmCode(e.target.value)}
            placeholder="000000"
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 font-mono text-sm tracking-widest text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-white/20"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setStep('status')}
            className="flex-1 rounded-full bg-white py-2 text-sm font-medium text-black"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={() => confirmMut.mutate()}
            disabled={confirmCode.length < 6 || confirmMut.isPending}
            className="bg-primary flex flex-1 items-center justify-center gap-2 rounded-full py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            <ShieldCheck className="h-4 w-4" />
            {t('profile.security.totp.confirm')}
          </button>
        </div>
      </div>
    )
  }

  if (step === 'backup') {
    return (
      <div className="space-y-4">
        <div>
          <p className="mb-1 text-sm font-medium text-green-400">{t('profile.security.totp.backupTitle')}</p>
          <p className="text-xs text-white/50">{t('profile.security.totp.backupNote')}</p>
        </div>
        <div className="grid grid-cols-2 gap-1.5 rounded-xl bg-white/5 p-3">
          {pendingBackups.map((code) => (
            <span key={code} className="font-mono text-xs text-white/80 text-center">{code}</span>
          ))}
        </div>
        <button
          onClick={() => { void navigator.clipboard.writeText(pendingBackups.join('\n\n')); toast.success(t('common.copied')) }}
          className="flex w-full items-center justify-center gap-2 rounded-full border border-white/10 py-2 text-sm font-medium text-white/60"
        >
          <Copy className="h-4 w-4" />
          {t('profile.security.totp.copyBackups')}
        </button>
        <button
          onClick={() => setStep('status')}
          className="bg-primary flex w-full items-center justify-center gap-2 rounded-full py-2 text-sm font-semibold text-white"
        >
          <ShieldCheck className="h-4 w-4" />
          {t('common.done')}
        </button>
      </div>
    )
  }

  if (step === 'disable') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-white/70">{t('profile.security.totp.disableInstruction')}</p>
        <input
          type="text"
          inputMode="numeric"
          maxLength={10}
          value={disableCode}
          onChange={(e) => setDisableCode(e.target.value)}
          placeholder="000000"
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 font-mono text-sm tracking-widest text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-white/20"
        />
        <div className="flex gap-2">
          <button
            onClick={() => setStep('status')}
            className="flex-1 rounded-full bg-white py-2 text-sm font-medium text-black"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={() => disableMut.mutate()}
            disabled={disableCode.length < 6 || disableMut.isPending}
            className="flex flex-1 items-center justify-center gap-2 rounded-full bg-red-500 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {disableMut.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <ShieldOff className="h-4 w-4" />
                {t('profile.security.totp.confirmDisable')}
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  return null
}

function SecurityPage() {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState<ExpandedRow>(null)
  const { data: totpStatus } = useQuery({
    queryKey: ['totp', 'status'],
    queryFn: () => totpApi.status(),
  })

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
          id="totp"
          icon={<Shield className={iconClass} />}
          label={t('profile.security.totp.title')}
          badge={totpStatus?.enabled ? <StatusChip label={t('profile.security.totp.enabled')} variant="redeemed" /> : undefined}
          expanded={expanded}
          onToggle={toggle}
        >
          <TotpSection />
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
