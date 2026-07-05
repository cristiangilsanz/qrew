import { useQuery } from '@tanstack/react-query'

import { onboardingApi } from '../api'

export function useOnboardingStatus(refetchInterval?: number) {
  return useQuery({
    queryKey: ['onboarding-status'],
    queryFn: onboardingApi.getStatus,
    refetchInterval,
  })
}
