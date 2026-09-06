// implements http
import axios, { type AxiosInstance, type CreateAxiosDefaults } from 'axios'

import { useAuthStore } from '@/store/auth'

import { attachRefreshInterceptor } from './refreshInterceptor'

interface ServiceClientOptions extends CreateAxiosDefaults {
  idempotencyKey?: boolean
  useSetupToken?: boolean
}

// implements create service client
export function createServiceClient({
  idempotencyKey = false,
  useSetupToken = false,
  ...axiosConfig
}: ServiceClientOptions): AxiosInstance {
  const client = axios.create({
    timeout: 10_000,
    headers: { 'Content-Type': 'application/json' },
    ...axiosConfig,
  })

  client.interceptors.request.use((config) => {
    const store = useAuthStore.getState()
    const token = store.accessToken ?? (useSetupToken ? store.setupToken : undefined)
    if (token && !config.headers.Authorization) config.headers.Authorization = `Bearer ${token}`
    if (idempotencyKey && (config.method === 'post' || config.method === 'patch')) {
      config.headers['Idempotency-Key'] = crypto.randomUUID()
    }
    return config
  })

  attachRefreshInterceptor(client)
  return client
}
