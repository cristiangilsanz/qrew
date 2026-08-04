import { useQuery } from '@tanstack/react-query'

import { marketApi } from '../api'

export function useMyQueues() {
  return useQuery({
    queryKey: ['market', 'queues'],
    queryFn: () => marketApi.getMyQueues(),
  })
}
