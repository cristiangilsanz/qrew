// provides use onboarding status
import { useQuery } from '@tanstack/react-query'

import { onboardingApi } from '../api'

// provides use onboarding status
export function useOnboardingStatus(refetchInterval?: number) {
  return useQuery({
    queryKey: ['onboarding-status'],
    queryFn: onboardingApi.getStatus,
    refetchInterval,
  })
}
