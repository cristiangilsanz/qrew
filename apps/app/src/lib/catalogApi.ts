import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

import { attachRefreshInterceptor } from './refreshInterceptor'

export const catalogClient = axios.create({
  baseURL: `${env.API_URL}/api/catalog`,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
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

catalogClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (config.method === 'post' || config.method === 'patch') {
    config.headers['Idempotency-Key'] = crypto.randomUUID()
  }
  return config
})

attachRefreshInterceptor(catalogClient)
