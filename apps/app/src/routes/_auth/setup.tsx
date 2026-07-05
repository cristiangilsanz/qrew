import { createFileRoute, redirect } from '@tanstack/react-router'

import { OnboardingWizard } from '@/features/onboarding/components/OnboardingWizard'
import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth/setup')({
  beforeLoad: () => {
    if (!useAuthStore.getState().isSetupPending) {
      throw redirect({ to: '/login' })
    }
  },
  component: OnboardingWizard,
})
