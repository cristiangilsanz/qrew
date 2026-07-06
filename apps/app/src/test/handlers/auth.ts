import { http, HttpResponse } from 'msw'

const API_URL = 'http://localhost:8001'

export const authHandlers = [
  http.post(`${API_URL}/v1/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      setup_required: false,
      password_compromised: false,
    })
  }),

  http.post(`${API_URL}/v1/auth/registration/`, () => {
    return HttpResponse.json(
      { id: 'mock-user-id', message: 'Account created. Please verify your email.' },
      { status: 201 },
    )
  }),

  http.post(`${API_URL}/v1/auth/passkeys/register/begin`, () => {
    return HttpResponse.json({
      challenge: 'mock-challenge',
      rp: { name: 'qrew', id: 'localhost' },
      user: { id: 'bW9jay11c2VyLWlk', name: 'test@example.com', displayName: 'Test User' },
      pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
      timeout: 60000,
      attestation: 'none',
    })
  }),

  http.post(`${API_URL}/v1/auth/passkeys/register/complete`, () => {
    return HttpResponse.json({ message: 'Passkey registered successfully.' })
  }),

  http.post(`${API_URL}/v1/auth/passkeys/authenticate/begin`, () => {
    return HttpResponse.json({
      challenge: 'mock-challenge',
      timeout: 60000,
      rpId: 'localhost',
      allowCredentials: [],
      userVerification: 'preferred',
    })
  }),

  http.post(`${API_URL}/v1/auth/passkeys/authenticate/complete`, () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      setup_required: false,
      password_compromised: false,
    })
  }),

  http.get(`${API_URL}/v1/auth/profile/me`, () => {
    return HttpResponse.json({
      id: 'mock-user-id',
      email: 'user@example.com',
      full_name: 'Test User',
      phone_number: '+34600000000',
      kyc_status: 'approved',
      email_verified: true,
      phone_verified: true,
      created_at: '2026-01-01T00:00:00Z',
    })
  }),

  http.post(`${API_URL}/v1/auth/account/change-password`, () =>
    HttpResponse.json({ message: 'Password changed successfully.' }),
  ),

  http.post(`${API_URL}/v1/auth/account/change-email`, () =>
    HttpResponse.json({ message: 'Confirmation link sent to your new email address.' }),
  ),

  http.post(`${API_URL}/v1/auth/account/confirm-email-change`, () =>
    HttpResponse.json({ message: 'Email address updated successfully.' }),
  ),

  http.post(`${API_URL}/v1/auth/account/change-phone`, () =>
    HttpResponse.json({ message: 'Verification code sent to your new phone number.' }),
  ),

  http.post(`${API_URL}/v1/auth/account/confirm-phone-change`, () =>
    HttpResponse.json({ message: 'Phone number updated successfully.' }),
  ),

  http.get(`${API_URL}/v1/auth/sessions`, () =>
    HttpResponse.json({
      items: [
        {
          id: 'session-1',
          jti: 'jti-1',
          ip_address: '192.168.1.1',
          user_agent: 'Mozilla/5.0 Chrome/120',
          device_fingerprint: null,
          created_at: '2026-07-01T10:00:00Z',
          last_used_at: '2026-07-06T10:00:00Z',
        },
      ],
      next_cursor: null,
    }),
  ),

  http.delete(`${API_URL}/v1/auth/sessions/:jti`, () => new HttpResponse(null, { status: 204 })),

  http.post(`${API_URL}/v1/auth/sessions/revoke-all`, () =>
    HttpResponse.json({ message: 'All sessions have been revoked.' }),
  ),

  http.post(`${API_URL}/v1/auth/account/delete`, () =>
    HttpResponse.json({ message: 'Account deleted.' }),
  ),

  http.get(`${API_URL}/v1/auth/passkeys/`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'mock-passkey-id',
          name: 'My MacBook',
          aaguid: '00000000-0000-0000-0000-000000000000',
          last_used_at: '2026-07-01T10:00:00Z',
          created_at: '2026-06-01T10:00:00Z',
        },
      ],
      next_cursor: null,
    })
  }),
]
