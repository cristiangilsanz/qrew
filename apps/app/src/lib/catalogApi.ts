import { env } from '@/config/env'

import { createServiceClient } from './http'

export const catalogClient = createServiceClient({
  baseURL: `${env.API_URL}/api/catalog`,
  idempotencyKey: true,
  paramsSerializer: (params) => {
    const sp = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue
      if (Array.isArray(value)) {
        value.forEach((v) => sp.append(key, String(v)))
      } else {
        sp.append(key, String(value))
      }
    }
    return sp.toString()
  },
})
