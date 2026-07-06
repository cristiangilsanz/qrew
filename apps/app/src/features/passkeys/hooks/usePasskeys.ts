import { useQuery } from '@tanstack/react-query'

import { passkeysApi } from '../api'

export function usePasskeys() {
  return useQuery({
    queryKey: ['passkeys'],
    queryFn: passkeysApi.list,
  })
}
