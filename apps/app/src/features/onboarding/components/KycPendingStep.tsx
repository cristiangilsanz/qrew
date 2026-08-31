// renders the kyc pending step component
import { useNavigate } from '@tanstack/react-router'
import { CheckCircle, Clock, RotateCw, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import { useCompleteSetup } from '../hooks/useCompleteSetup'
import { useOnboardingStatus } from '../hooks/useOnboardingStatus'

interface Props {
  onRetry: () => void
}

// renders the kyc pending step component
export function KycPendingStep({ onRetry }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: status } = useOnboardingStatus(10_000)
  // implements complete setup
  const completeSetup = useCompleteSetup(() => navigate({ to: '/home' }))

  if (status?.kyc_status === 'rejected') {
    return (
      <div className="space-y-4 text-center">
        <XCircle className="text-destructive mx-auto h-12 w-12" />
        <div>
          <p className="font-semibold">{t('onboarding.pending.rejected')}</p>
          <p className="text-muted-foreground text-sm">
            {t('onboarding.pending.rejectedDescription')}
          </p>
        </div>
        <Button variant="outline" className="w-full rounded-full" onClick={onRetry}>
          <RotateCw className="mr-2 h-4 w-4" />
          {t('onboarding.pending.retry')}
        </Button>
      </div>
    )
  }

  const approved = status?.kyc_status === 'approved'

  return (
    <div className="space-y-4 text-center">
      {approved ? (
        <CheckCircle className="text-primary mx-auto h-12 w-12" />
      ) : (
        <Clock className="text-muted-foreground mx-auto h-12 w-12 animate-pulse" />
      )}
      <div>
        <p className="font-semibold">
          {approved ? t('onboarding.pending.approved') : t('onboarding.pending.title')}
        </p>
        <p className="text-muted-foreground text-sm">
          {approved
            ? t('onboarding.pending.approvedDescription')
            : t('onboarding.pending.description')}
        </p>
      </div>
      {status?.is_complete && (
        <Button
          className="w-full rounded-full"
          isLoading={completeSetup.isPending}
          onClick={() => completeSetup.mutate()}
        >
          <CheckCircle className="mr-2 h-4 w-4" />
          {t('onboarding.pending.continue')}
        </Button>
      )}
    </div>
  )
}
