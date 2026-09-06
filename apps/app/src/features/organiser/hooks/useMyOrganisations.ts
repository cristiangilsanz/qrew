// provides use my organisations
import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

// provides use my organisations
export function useMyOrganisations() {
  return useQuery({
    queryKey: ['organisations'],
    queryFn: organiserApi.listMyOrgs,
  })
}
