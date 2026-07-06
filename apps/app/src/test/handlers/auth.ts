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
