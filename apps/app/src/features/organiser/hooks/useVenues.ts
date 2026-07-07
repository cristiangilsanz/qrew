import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

export function useVenues() {
  return useQuery({
    queryKey: ['venues'],
    queryFn: organiserApi.listVenues,
  })
}
