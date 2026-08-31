// implements profile api
import { apiClient } from '@/lib/api'

export interface UserPublicProfile {
  id: string
  full_name: string
  email: string
}

export interface UserSearchResult {
  id: string
  email: string
  full_name: string
}

export interface UserProfile {
  id: string
  email: string
  full_name: string
  phone_number: string
  kyc_status: 'not_submitted' | 'pending' | 'approved' | 'rejected'
  email_verified: boolean
  phone_verified: boolean
  is_admin: boolean
  created_at: string
}

export interface AuditEvent {
  id: string
  action: string
  entity_type: string | null
  summary: string
  ip_address: string | null
  device_fingerprint_hash: string | null
  created_at: string
}

export interface Device {
  id: string
  name: string
  created_at: string
  last_seen_at: string | null
  is_current: boolean
}

export interface Session {
  id: string
  jti: string
  ip_address: string | null
  user_agent: string | null
  device_fingerprint: string | null
  created_at: string
  last_used_at: string
  is_current: boolean
  location: string | null
}

export const profileApi = {
  // implements get me
  getMe: () => apiClient.get<UserProfile>('/v1/auth/profile/me').then((r) => r.data),

  // implements change password
  changePassword: (data: { current_password: string; new_password: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/change-password', data)
      .then((r) => r.data),

  // implements change email
  changeEmail: (data: { new_email: string; current_password: string }) =>
    apiClient.post<{ message: string }>('/v1/auth/account/change-email', data).then((r) => r.data),

  // implements confirm email change
  confirmEmailChange: (token: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/confirm-email-change', { token })
      .then((r) => r.data),

  // implements change phone
  changePhone: (data: { new_phone_number: string; current_password: string }) =>
    apiClient.post<{ message: string }>('/v1/auth/account/change-phone', data).then((r) => r.data),

  // implements confirm phone change
  confirmPhoneChange: (data: { new_phone_number: string; otp: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/confirm-phone-change', data)
      .then((r) => r.data),

  // implements get sessions
  getSessions: () =>
    apiClient
      .get<{ items: Session[]; next_cursor: string | null }>('/v1/auth/sessions')
      .then((r) => r.data),

  // implements revoke session
  revokeSession: (jti: string) => apiClient.delete(`/v1/auth/sessions/${jti}`),

  // implements revoke all sessions
  revokeAllSessions: () =>
    apiClient.post<{ message: string }>('/v1/auth/sessions/revoke-all').then((r) => r.data),

  // implements delete account
  deleteAccount: (current_password: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/delete', { current_password })
      .then((r) => r.data),

  // implements get audit log
  getAuditLog: (cursor?: string) =>
    apiClient
      .get<{ items: AuditEvent[]; next_cursor: string | null }>('/v1/auth/profile/audit', {
        params: cursor ? { cursor } : {},
      })
      .then((r) => r.data),

  // implements get devices
  getDevices: () =>
    apiClient
      .get<{ items: Device[]; next_cursor: string | null }>('/v1/auth/devices')
      .then((r) => r.data),

  // asks the server for the challenge this device has to sign
  beginDeviceBind: () =>
    apiClient.post<{ challenge: string }>('/v1/auth/devices/bind/begin').then((r) => r.data),

  // hands over the signed challenge so the device becomes trusted
  completeDeviceBind: (body: { name: string; public_key: string; signature: string }) =>
    apiClient
      .post<{ device_id: string; message: string }>('/v1/auth/devices/bind/complete', body)
      .then((r) => r.data),

  // implements revoke device
  revokeDevice: (deviceId: string) =>
    apiClient.post<{ message: string }>(`/v1/auth/devices/${deviceId}/revoke`).then((r) => r.data),

  // implements revoke all devices
  revokeAllDevices: () =>
    apiClient.post<{ message: string }>('/v1/auth/devices/revoke-all').then((r) => r.data),

  // implements get public profiles
  getPublicProfiles: (userIds: string[]) =>
    apiClient
      .post<UserPublicProfile[]>('/v1/auth/profile/users/public', { user_ids: userIds })
      .then((r) => r.data),

  // implements search users
  searchUsers: (q: string) =>
    apiClient
      .get<UserSearchResult[]>('/v1/admin/users/search', { params: { q } })
      .then((r) => r.data),
}
