// implements setup
import { createFileRoute, redirect } from '@tanstack/react-router'

import { OnboardingWizard } from '@/features/onboarding/components/OnboardingWizard'
import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth/setup')({
  // implements before load
  beforeLoad: () => {
    if (!useAuthStore.getState().isSetupPending) {
      throw redirect({ to: '/login' })
    }
  },
  component: OnboardingWizard,
})
