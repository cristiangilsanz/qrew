// implements payments api
import { env } from '@/config/env'

import { createServiceClient } from './http'

export const paymentsClient = createServiceClient({
  baseURL: `${env.API_URL}/api/payments`,
})
