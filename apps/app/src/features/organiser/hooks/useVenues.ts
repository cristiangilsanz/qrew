// provides use venues
import { useQuery } from '@tanstack/react-query'

import { organiserApi } from '../api'

// provides use venues
export function useVenues() {
  return useQuery({
    queryKey: ['venues'],
    queryFn: organiserApi.listVenues,
  })
}
