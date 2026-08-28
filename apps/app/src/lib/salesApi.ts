// implements sales api
import { env } from '@/config/env'

import { createServiceClient } from './http'

export const salesClient = createServiceClient({
  baseURL: `${env.API_URL}/api/sales`,
  idempotencyKey: true,
})
