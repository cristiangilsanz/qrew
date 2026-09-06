// implements the account recovery api
import { apiClient } from '@/lib/api'

export interface RecoveryBeginResponse {
  recovery_token: string | null
  passkey_options: string | null
}

export const recoveryApi = {
  // implements begin
  begin: (input: { email: string; file: File }) => {
    const formData = new FormData()
    formData.append('email', input.email)
    formData.append('document', input.file)
    return apiClient
      .post<RecoveryBeginResponse>('/v1/auth/recovery/begin', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  // implements complete
  complete: (recoveryToken: string, credential: object) =>
    apiClient
      .post<{ message: string }>('/v1/auth/recovery/complete', credential, {
        headers: { Authorization: `Bearer ${recoveryToken}` },
        // the recovery token is the credential here, so a stale session must not
        // be refreshed over it
        _ownAuth: true,
      } as never)
      .then((r) => r.data),
}
