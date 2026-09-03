// implements the passkey re-assertion api
import { apiClient } from '@/lib/api'

export interface AssertCompleteResponse {
  asserted_at: string
  access_token: string
}

// the options come back as the json webauthn expects, so they stay loosely typed
// and each consumer narrows only the fields it hands to the authenticator
export interface AssertOptions {
  challenge: string
  rpId: string
  userVerification?: 'required' | 'preferred' | 'discouraged'
  [key: string]: unknown
}

export const reassertApi = {
  // implements begin
  begin: () =>
    apiClient
      .post<{ options: string }>('/v1/auth/passkeys/assert/begin')
      .then((r) => JSON.parse(r.data.options) as AssertOptions),

  // implements complete
  complete: (credential: object) =>
    apiClient
      .post<AssertCompleteResponse>('/v1/auth/passkeys/assert/complete', credential)
      .then((r) => r.data),
}
