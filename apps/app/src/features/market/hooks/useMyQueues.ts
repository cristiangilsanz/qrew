// provides use my queues
import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

// provides use my queues
export function useMyQueues() {
  return useQuery({
    queryKey: ['market', 'queues'],
    // implements query fn
    queryFn: () => marketApi.getMyQueues(),
  })
}
