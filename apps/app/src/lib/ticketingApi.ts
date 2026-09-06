// implements ticketing api
import { env } from '@/config/env'

import { createServiceClient } from './http'

export const ticketingClient = createServiceClient({
  baseURL: `${env.API_URL}/api/ticketing`,
})
