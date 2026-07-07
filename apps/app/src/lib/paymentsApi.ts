import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

export const paymentsClient = axios.create({
  baseURL: env.PAYMENTS_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

paymentsClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
