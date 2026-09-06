// implements scanner api
import axios from 'axios'

import { env } from '@/config/env'
import { useAuthStore } from '@/store/auth'

export const entryClient = axios.create({
  baseURL: `${env.API_URL}/api/entry`,
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

export interface EntryStats {
  event_id: string
  since: string
  total_issued: number
  total_entered: number
  total_remaining: number
  rejections_by_reason: Record<string, number>
  last_scan_at: string | null
}

export const scannerApi = {
  // implements create for event
  createForEvent: (eventId: string, name: string, date?: string) =>
    entryClient
      .post<ScannerToken>(`/v1/scanners/for-event/${eventId}`, { name, date })
      .then((r) => r.data),

  // implements refresh
  refresh: (scannerToken: string) =>
    axios
      .post<ScannerToken>(
        `${env.API_URL}/api/entry/v1/scanners/refresh`,
        {},
        { headers: { Authorization: `Bearer ${scannerToken}` } },
      )
      .then((r) => r.data),

  // implements validate entry
  validateEntry: (scannerToken: string, ticketJwt: string) =>
    axios
      .post<EntryResult>(
        `${env.API_URL}/api/entry/v1/entry/validate`,
        { ticket_jwt: ticketJwt },
        { headers: { Authorization: `Bearer ${scannerToken}` } },
      )
      .then((r) => r.data),

  // implements get entry stats
  getEntryStats: (eventId: string) =>
    entryClient.get<EntryStats>(`/v1/events/${eventId}/entry-stats`).then((r) => r.data),
}
