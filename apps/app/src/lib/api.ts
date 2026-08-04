import { env } from '@/config/env'

import { createServiceClient } from './http'

export const apiClient = createServiceClient({
  baseURL: `${env.API_URL}/api/identity`,
  useSetupToken: true,
})
