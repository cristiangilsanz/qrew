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
}

export interface Session {
  id: string
  jti: string
  ip_address: string | null
  user_agent: string | null
  device_fingerprint: string | null
  created_at: string
  last_used_at: string
}

export const profileApi = {
  getMe: () => apiClient.get<UserProfile>('/v1/auth/profile/me').then((r) => r.data),

  changePassword: (data: { current_password: string; new_password: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/change-password', data)
      .then((r) => r.data),

  changeEmail: (data: { new_email: string; current_password: string }) =>
    apiClient.post<{ message: string }>('/v1/auth/account/change-email', data).then((r) => r.data),

  confirmEmailChange: (token: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/confirm-email-change', { token })
      .then((r) => r.data),

  changePhone: (data: { new_phone_number: string; current_password: string }) =>
    apiClient.post<{ message: string }>('/v1/auth/account/change-phone', data).then((r) => r.data),

  confirmPhoneChange: (data: { new_phone_number: string; otp: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/confirm-phone-change', data)
      .then((r) => r.data),

  getSessions: () =>
    apiClient
      .get<{ items: Session[]; next_cursor: string | null }>('/v1/auth/sessions')
      .then((r) => r.data),

  revokeSession: (jti: string) => apiClient.delete(`/v1/auth/sessions/${jti}`),

  revokeAllSessions: () =>
    apiClient.post<{ message: string }>('/v1/auth/sessions/revoke-all').then((r) => r.data),

  deleteAccount: (current_password: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/delete', { current_password })
      .then((r) => r.data),

  getAuditLog: (cursor?: string) =>
    apiClient
      .get<{ items: AuditEvent[]; next_cursor: string | null }>('/v1/auth/profile/audit', {
        params: cursor ? { cursor } : {},
      })
      .then((r) => r.data),

  getDevices: () =>
    apiClient
      .get<{ items: Device[]; next_cursor: string | null }>('/v1/auth/devices')
      .then((r) => r.data),

  revokeDevice: (deviceId: string) =>
    apiClient.post<{ message: string }>(`/v1/auth/devices/${deviceId}/revoke`).then((r) => r.data),

  revokeAllDevices: () =>
    apiClient.post<{ message: string }>('/v1/auth/devices/revoke-all').then((r) => r.data),

  getPublicProfiles: (userIds: string[]) =>
    apiClient
      .post<UserPublicProfile[]>('/v1/auth/profile/users/public', { user_ids: userIds })
      .then((r) => r.data),

  searchUsers: (q: string) =>
    apiClient
      .get<UserSearchResult[]>('/v1/admin/users/search', { params: { q } })
      .then((r) => r.data),
}
