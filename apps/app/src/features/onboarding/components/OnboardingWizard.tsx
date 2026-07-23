import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { OnboardingStepSkeleton } from '@/components/ui/skeleton'
import { AuthLayout } from '@/features/auth/components/AuthLayout'

import { type KycUploadResponse } from '../api'
import { useOnboardingStatus } from '../hooks/useOnboardingStatus'
import { EmailVerificationStep } from './EmailVerificationStep'
import { KycPendingStep } from './KycPendingStep'
import { KycUploadStep } from './KycUploadStep'
import { PasskeyRegistrationStep } from './PasskeyRegistrationStep'
import { PhoneVerificationStep } from './PhoneVerificationStep'

const STEPS = ['email', 'phone', 'kyc', 'passkey'] as const
type Step = (typeof STEPS)[number]

function StepIndicator({ current }: { current: Step | 'pending' }) {
  const { t } = useTranslation()
  const labels: Record<Step, string> = {
    email: t('onboarding.steps.email'),
    phone: t('onboarding.steps.phone'),
    kyc: t('onboarding.steps.kyc'),
    passkey: t('onboarding.steps.passkey'),
  }
  const currentIndex = STEPS.indexOf(current as Step)

  return (
    <div className="mb-6 flex items-center justify-between gap-2">
      {STEPS.map((step, i) => {
        const done = currentIndex > i || current === 'pending'
        const active = currentIndex === i
        return (
          <div key={step} className="flex flex-1 flex-col items-center gap-1">
            <div
              className={[
                'flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors',
                done
                  ? 'bg-primary text-primary-foreground'
                  : active
                    ? 'border-primary text-primary border-2'
                    : 'border-border text-muted-foreground border-2',
              ].join(' ')}
            >
              {done ? '✓' : i + 1}
            </div>
            <span
              className={[
                'text-center text-xs',
                active || done ? 'text-foreground font-medium' : 'text-muted-foreground',
              ].join(' ')}
            >
              {labels[step]}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function OnboardingWizard() {
  const { t } = useTranslation()
  const { data: status, isLoading, refetch } = useOnboardingStatus()
  const [kycRetry, setKycRetry] = useState(false)

  const currentStep: Step | 'pending' = kycRetry ? 'kyc' : (status?.current_step ?? 'email')

  const handleStepSuccess = () => {
    setKycRetry(false)
    void refetch()
  }

  const handleKycSuccess = (data: KycUploadResponse) => {
    if (data.kyc_status !== 'not_submitted') {
      setKycRetry(false)
      void refetch()
    }
  }

  if (isLoading) {
    return (
      <AuthLayout title={t('onboarding.title')} subtitle={t('onboarding.subtitle')}>
        <OnboardingStepSkeleton />
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title={t('onboarding.title')} subtitle={t('onboarding.subtitle')}>
      <StepIndicator current={currentStep} />

      {currentStep === 'email' && <EmailVerificationStep onSuccess={handleStepSuccess} />}
      {currentStep === 'phone' && <PhoneVerificationStep onSuccess={handleStepSuccess} />}
      {currentStep === 'kyc' && <KycUploadStep onSuccess={handleKycSuccess} />}
      {currentStep === 'passkey' && <PasskeyRegistrationStep onSuccess={handleStepSuccess} />}
      {currentStep === 'pending' && (
        <KycPendingStep
          onRetry={() => {
            setKycRetry(true)
          }}
        />
      )}
    </AuthLayout>
  )
}
