import type { AxiosInstance } from 'axios'
import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

let refreshPromise: Promise<string> | null = null

async function doRefresh(): Promise<string> {
  const refreshToken = useAuthStore.getState().refreshToken
  if (!refreshToken) throw new Error('No refresh token')

  const res = await axios.post<{ access_token: string; refresh_token: string }>(
    `${env.API_URL}/api/identity/v1/auth/refresh`,
    { refresh_token: refreshToken },
  )
  useAuthStore.getState().setTokens(res.data.access_token, res.data.refresh_token)
  return res.data.access_token
}

export function attachRefreshInterceptor(client: AxiosInstance): void {
  client.interceptors.response.use(
    (response) => response,
    async (error: unknown) => {
      if (!axios.isAxiosError(error)) return Promise.reject(error)
      const status = error.response?.status
      const config = error.config
      if (status !== 401 || !config || (config as { _retry?: boolean })._retry) {
        return Promise.reject(error)
      }
      ;(config as { _retry?: boolean })._retry = true
      try {
        if (!refreshPromise) {
          refreshPromise = doRefresh().finally(() => {
            refreshPromise = null
          })
        }
        const newToken = await refreshPromise
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${newToken}`
        return client(config)
      } catch {
        useAuthStore.getState().clearSession()
        window.location.replace('/login')
        return Promise.reject(error)
      }
    },
  )
}
