import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

export function useMyOrganisations() {
  return useQuery({
    queryKey: ['organisations'],
    queryFn: organiserApi.listMyOrgs,
  })
}
