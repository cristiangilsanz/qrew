import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

export const entryClient = axios.create({
  baseURL: env.ENTRY_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

entryClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export interface ScannerToken {
  scanner_id: string
  token: string
  token_type: string
  expires_in_hours: number
}

export interface EntryResult {
  allowed: boolean
  reason: string | null
  ticket_id: string | null
  holder_user_id: string | null
  scanned_at: string
}

export const scannerApi = {
  createForEvent: (eventId: string, name: string, date?: string) =>
    entryClient
      .post<ScannerToken>(`/v1/scanners/for-event/${eventId}`, { name, date })
      .then((r) => r.data),

  validateEntry: (scannerToken: string, ticketJwt: string) =>
    axios
      .post<EntryResult>(
        `${env.ENTRY_URL}/v1/entry/validate`,
        { ticket_jwt: ticketJwt },
        { headers: { Authorization: `Bearer ${scannerToken}` } },
      )
      .then((r) => r.data),
}
