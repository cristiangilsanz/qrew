import { useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { Calendar, ChevronRight, Mail, Phone, ShieldCheck, User } from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { KycUploadStep } from '@/features/onboarding/components/KycUploadStep'
import { useOnboardingStatus } from '@/features/onboarding/hooks/useOnboardingStatus'
import { ChangeEmailForm } from '@/features/profile/components/ChangeEmailForm'
import { ChangePhoneForm } from '@/features/profile/components/ChangePhoneForm'
import { useProfile } from '@/features/profile/hooks/useProfile'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/profile/account')({
  component: AccountPage,
})

type ExpandedRow = 'email' | 'phone' | 'kyc' | null

type KycStatus = 'not_submitted' | 'pending' | 'approved' | 'rejected'

const kycChipStyles: Record<KycStatus, string> = {
  approved: 'bg-green-500/20 text-green-400',
  pending: 'bg-amber-500/20 text-amber-400',
  rejected: 'bg-red-500/20 text-red-400',
  not_submitted: 'bg-white/10 text-muted-foreground',
}

const expandVariants = {
  hidden: { height: 0, opacity: 0 },
  visible: { height: 'auto', opacity: 1, transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] } },
  exit: { height: 0, opacity: 0, transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] } },
}

function VerifiedChip({ verified }: { verified: boolean }) {
  const { t } = useTranslation()
  return (
    <span
      className={cn(
        'rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase',
        verified ? 'bg-green-500/20 text-green-400' : 'text-muted-foreground bg-white/10',
      )}
    >
      {verified ? t('profile.verified') : t('profile.unverified')}
    </span>
  )
}

function KycStatusChip({ status }: { status: KycStatus }) {
  const { t } = useTranslation()
  return (
    <span
      className={cn(
        'rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase',
        kycChipStyles[status],
      )}
    >
      {t(`profile.kycStatus.${status}`)}
    </span>
  )
}

function Row({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 px-4 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
        {icon}
      </div>
      <span className="text-muted-foreground w-20 shrink-0 text-sm">{label}</span>
      <div className="flex flex-1 justify-end">{children}</div>
    </div>
  )
}

function ExpandableRow({
  icon,
  label,
  value,
  verified,
  isOpen,
  onToggle,
  children,
}: {
  icon: ReactNode
  label: string
  value: string
  verified?: boolean
  isOpen: boolean
  onToggle: () => void
  children: ReactNode
}) {
  return (
    <>
      <button onClick={onToggle} className="flex w-full items-center gap-3 px-4 py-4 text-left">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
          {icon}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <span className="text-muted-foreground w-10 shrink-0 text-sm">{label}</span>
          {verified !== undefined && <VerifiedChip verified={verified} />}
        </div>
        <div className="flex flex-1 items-center justify-end gap-2 overflow-hidden">
          <span className={cn('truncate text-sm font-medium', isOpen && 'text-primary')}>
            {value}
          </span>
          <ChevronRight
            className={cn(
              'text-muted-foreground h-4 w-4 shrink-0 transition-transform duration-200',
              isOpen && 'text-primary rotate-90',
            )}
          />
        </div>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            variants={expandVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{ overflow: 'hidden' }}
          >
            <div className="border-t border-white/10 bg-white/[0.03] px-4 pt-4 pb-5">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function AccountPage() {
  const { t, i18n } = useTranslation()
  const { data: profile, isLoading } = useProfile()
  const { data: onboarding } = useOnboardingStatus()
  const [expanded, setExpanded] = useState<ExpandedRow>(null)
  const queryClient = useQueryClient()

  const toggle = (row: ExpandedRow) => setExpanded((prev) => (prev === row ? null : row))

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  if (!profile) return null

  const memberSince = new Date(profile.created_at).toLocaleDateString(i18n.language, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  const iconClass = 'h-4 w-4 text-muted-foreground'

  return (
    <div className="min-h-screen px-4 pt-4 pb-28">
      <BackButton to="/profile" className="mb-6" />
      <h1 className="mb-6 text-xl font-bold">{t('profile.account.title')}</h1>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <Row icon={<User className={iconClass} />} label={t('profile.account.fullName')}>
          <span className="text-sm font-medium">{profile.full_name}</span>
        </Row>

        <div className="mx-4 border-t border-white/10" />

        <Row icon={<Calendar className={iconClass} />} label={t('profile.account.createdAt')}>
          <span className="text-sm font-medium">{memberSince}</span>
        </Row>

        <div className="mx-4 border-t border-white/10" />

        {/* KYC / Identity verification row */}
        {profile.kyc_status === 'rejected' || profile.kyc_status === 'not_submitted' ? (
          <>
            <button
              onClick={() => toggle('kyc')}
              className="flex w-full items-center gap-3 px-4 py-4 text-left"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
                <ShieldCheck className={iconClass} />
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span className="text-muted-foreground w-10 shrink-0 text-sm">
                  {t('profile.kycStatus.rowLabel')}
                </span>
                <KycStatusChip status={profile.kyc_status} />
              </div>
              <div className="flex flex-1 justify-end">
                <ChevronRight
                  className={cn(
                    'text-muted-foreground h-4 w-4 shrink-0 transition-transform duration-200',
                    expanded === 'kyc' && 'text-primary rotate-90',
                  )}
                />
              </div>
            </button>
            <AnimatePresence initial={false}>
              {expanded === 'kyc' && (
                <motion.div
                  variants={expandVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  style={{ overflow: 'hidden' }}
                >
                  <div className="border-t border-white/10 bg-white/[0.03] px-4 pt-4 pb-5">
                    <p className="text-muted-foreground mb-4 text-sm">
                      {t('profile.kycStatus.description')}
                    </p>
                    <KycUploadStep
                      onSuccess={() => {
                        void queryClient.invalidateQueries({ queryKey: ['profile'] })
                        toggle('kyc')
                      }}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        ) : (
          <div className="flex items-center gap-3 px-4 py-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
              <ShieldCheck className={iconClass} />
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <span className="text-muted-foreground w-10 shrink-0 text-sm">
                {t('profile.kycStatus.rowLabel')}
              </span>
              <KycStatusChip status={profile.kyc_status} />
            </div>
          </div>
        )}

        <div className="mx-4 border-t border-white/10" />

        <ExpandableRow
          icon={<Mail className={iconClass} />}
          label={t('profile.account.emailLabel')}
          value={profile.email}
          verified={onboarding?.email_verified}
          isOpen={expanded === 'email'}
          onToggle={() => toggle('email')}
        >
          <ChangeEmailForm hideTitle />
        </ExpandableRow>

        <div className="mx-4 border-t border-white/10" />

        <ExpandableRow
          icon={<Phone className={iconClass} />}
          label={t('profile.account.phoneLabel')}
          value={profile.phone_number}
          verified={onboarding?.phone_verified}
          isOpen={expanded === 'phone'}
          onToggle={() => toggle('phone')}
        >
          <ChangePhoneForm hideTitle />
        </ExpandableRow>
      </div>
    </div>
  )
}
