import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

export const ticketingClient = axios.create({ baseURL: env.TICKETING_URL })

ticketingClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
