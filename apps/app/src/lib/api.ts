import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

import { attachRefreshInterceptor } from './refreshInterceptor'

export const apiClient = axios.create({
  baseURL: `${env.API_URL}/api/identity`,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken ?? useAuthStore.getState().setupToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

attachRefreshInterceptor(apiClient)
