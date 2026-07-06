import axios from 'axios'

import { env } from '@/config/env'

export const catalogClient = axios.create({
  baseURL: env.CATALOG_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})
