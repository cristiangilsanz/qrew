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
  password_compromised: boolean
}

export interface RegisterRequest {
  full_name: string
  email: string
  phone_number: string
  password: string
  terms_accepted: boolean
}

export interface RegisterResponse {
  id: string
  message: string
}

// Pydantic validation error item shape from FastAPI 422 responses
interface PydanticErrorItem {
  type: string
  loc: string[]
  msg: string
  input?: unknown
}

export type ApiErrorDetail = string | PydanticErrorItem[]

export function extractErrorMessage(detail: ApiErrorDetail | undefined, fallback: string): string {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  return detail[0]?.msg ?? fallback
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/v1/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    apiClient
      .post<RegisterResponse>('/v1/auth/registration/', { ...data, captcha_token: 'dev-bypass' })
      .then((r) => r.data),
}
