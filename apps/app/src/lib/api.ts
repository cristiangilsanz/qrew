import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

export const apiClient = axios.create({
  baseURL: env.API_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken ?? useAuthStore.getState().setupToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url
    const detail = error.response?.data?.detail
    console.error(`[api] ${status ?? 'network'} ${url}`, detail ?? error.message)
    if (status === 401) {
      useAuthStore.getState().clearSession()
    }
    return Promise.reject(error)
  },
)
