import { apiClient } from '@/lib/api'

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
}
