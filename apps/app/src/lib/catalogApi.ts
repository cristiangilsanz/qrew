import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

export const catalogClient = axios.create({
  baseURL: env.CATALOG_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

catalogClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (config.method === 'post' || config.method === 'patch') {
    config.headers['Idempotency-Key'] = crypto.randomUUID()
  }
  return config
})
