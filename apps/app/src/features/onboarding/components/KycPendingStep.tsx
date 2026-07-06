import { useNavigate } from '@tanstack/react-router'
import { CheckCircle, Clock, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import { useCompleteSetup } from '../hooks/useCompleteSetup'
import { useOnboardingStatus } from '../hooks/useOnboardingStatus'

interface Props {
  onRetry: () => void
}

export function KycPendingStep({ onRetry }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: status } = useOnboardingStatus(10_000)
  const completeSetup = useCompleteSetup(() => navigate({ to: '/events' }))

  if (status?.is_complete) {
    return (
      <div className="space-y-4 text-center">
        <CheckCircle className="text-primary mx-auto h-12 w-12" />
        <div>
          <p className="font-semibold">{t('onboarding.pending.approved')}</p>
          <p className="text-muted-foreground text-sm">
            {t('onboarding.pending.approvedDescription')}
          </p>
        </div>
        <Button
          className="w-full"
          isLoading={completeSetup.isPending}
          onClick={() => completeSetup.mutate()}
        >
          {t('onboarding.pending.continue')}
        </Button>
      </div>
    )
  }

  if (status && !status.kyc_submitted) {
    return (
      <div className="space-y-4 text-center">
        <XCircle className="text-destructive mx-auto h-12 w-12" />
        <div>
          <p className="font-semibold">{t('onboarding.pending.rejected')}</p>
          <p className="text-muted-foreground text-sm">
            {t('onboarding.pending.rejectedDescription')}
          </p>
        </div>
        <Button variant="outline" className="w-full" onClick={onRetry}>
          {t('onboarding.pending.retry')}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 text-center">
      <Clock className="text-muted-foreground mx-auto h-12 w-12 animate-pulse" />
      <div>
        <p className="font-semibold">{t('onboarding.pending.title')}</p>
        <p className="text-muted-foreground text-sm">{t('onboarding.pending.description')}</p>
      </div>
    </div>
  )
}
