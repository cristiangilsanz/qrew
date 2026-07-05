import { apiClient } from '@/lib/api'

export interface OnboardingStatus {
  email_verified: boolean
  phone_verified: boolean
  kyc_submitted: boolean
  passkey_registered: boolean
  is_complete: boolean
}

export interface KycUploadResponse {
  message: string
  kyc_status: 'pending' | 'approved' | 'rejected' | 'not_submitted'
}

export interface CompleteSetupResponse {
  access_token: string
  refresh_token: string | null
  token_type: string
  setup_required: boolean
  password_compromised: boolean
}

export const onboardingApi = {
  getStatus: () =>
    apiClient.get<OnboardingStatus>('/v1/auth/profile/onboarding-status').then((r) => r.data),

  verifyEmail: (data: { token: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/registration/verify-email', data)
      .then((r) => r.data),

  verifyPhone: (data: { phone_number: string; otp: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/registration/verify-phone', data)
      .then((r) => r.data),

  resendPhoneOtp: (data: { phone_number: string }) =>
    apiClient
      .post<{ message: string }>('/v1/auth/registration/resend-phone-otp', data)
      .then((r) => r.data),

  uploadKyc: (file: File) => {
    const formData = new FormData()
    formData.append('document', file)
    return apiClient
      .post<KycUploadResponse>('/v1/auth/setup/kyc/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  completeSetup: () =>
    apiClient.post<CompleteSetupResponse>('/v1/auth/setup/complete-setup').then((r) => r.data),
}
