// implements auth api
import { apiClient } from '@/lib/api'

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string | null
  token_type: string
  setup_required: boolean
  totp_required: boolean
  password_compromised: boolean
}

export interface TotpSetupResponse {
  provisioning_uri: string
  backup_codes: string[]
  secret: string
}

export interface TotpVerifyResponse {
  access_token: string
  refresh_token: string
}

export interface TotpStatusResponse {
  enabled: boolean
}

export interface RegisterRequest {
  full_name: string
  email: string
  phone_number: string
  password: string
  terms_accepted: boolean
  captcha_token: string
}

export interface RegisterResponse {
  id: string
  message: string
}

interface PydanticErrorItem {
  type: string
  loc: string[]
  msg: string
  input?: unknown
}

export type ApiErrorDetail = string | PydanticErrorItem[]

// implements extract error message
export function extractErrorMessage(detail: ApiErrorDetail | undefined, fallback: string): string {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  return detail[0]?.msg ?? fallback
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
}

export const authApi = {
  // implements login
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/v1/auth/login', data).then((r) => r.data),

  // implements refresh
  refresh: (refreshToken: string) =>
    apiClient
      .post<RefreshResponse>('/v1/auth/refresh', { refresh_token: refreshToken })
      .then((r) => r.data),

  // implements register
  register: (data: RegisterRequest) =>
    apiClient.post<RegisterResponse>('/v1/auth/registration/', data).then((r) => r.data),

  // implements passkey auth begin
  passkeyAuthBegin: (email: string) =>
    apiClient.post('/v1/auth/passkeys/authenticate/begin', { email }).then((r) => r.data),

  // implements passkey auth complete
  passkeyAuthComplete: (credential: object) =>
    apiClient
      .post<LoginResponse>('/v1/auth/passkeys/authenticate/complete', credential)
      .then((r) => r.data),

  // implements logout
  logout: (refreshToken: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/logout', { refresh_token: refreshToken })
      .then((r) => r.data),

  // implements forgot password
  forgotPassword: (email: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/forgot-password', { email })
      .then((r) => r.data),

  // implements reset password
  resetPassword: (token: string, newPassword: string) =>
    apiClient
      .post<{ message: string }>('/v1/auth/account/reset-password', {
        token,
        new_password: newPassword,
      })
      .then((r) => r.data),
}

export const totpApi = {
  // implements status
  status: () => apiClient.get<TotpStatusResponse>('/v1/auth/totp/status').then((r) => r.data),

  // implements setup
  setup: () => apiClient.post<TotpSetupResponse>('/v1/auth/totp/setup').then((r) => r.data),

  // implements confirm
  confirm: (secret: string, code: string, backupCodes: string[]) =>
    apiClient
      .post<{ message: string }>('/v1/auth/totp/confirm', {
        secret,
        code,
        backup_codes: backupCodes,
      })
      .then((r) => r.data),

  // implements verify
  verify: (totpToken: string, code: string) =>
    apiClient
      .post<TotpVerifyResponse>(
        '/v1/auth/totp/verify',
        { code },
        { headers: { Authorization: `Bearer ${totpToken}` } },
      )
      .then((r) => r.data),

  // implements disable
  disable: (code: string) =>
    apiClient
      .delete<{ message: string }>('/v1/auth/totp/disable', { data: { code } })
      .then((r) => r.data),
}
