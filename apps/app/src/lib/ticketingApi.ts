import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

import { attachRefreshInterceptor } from './refreshInterceptor'

export const ticketingClient = axios.create({ baseURL: `${env.API_URL}/api/ticketing` })

ticketingClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

attachRefreshInterceptor(ticketingClient)
