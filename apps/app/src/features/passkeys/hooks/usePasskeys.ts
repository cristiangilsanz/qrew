// provides use passkeys
import { useQuery } from '@tanstack/react-query'

import { passkeysApi } from '../api'

// provides use passkeys
export function usePasskeys() {
  return useQuery({
    queryKey: ['passkeys'],
    queryFn: passkeysApi.list,
  })
}
