import { http, HttpResponse } from 'msw'

const API_URL = 'http://localhost:8000/api/identity'

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

  http.get(`${API_URL}/v1/auth/profile/onboarding-status`, () =>
    HttpResponse.json({
      email_verified: true,
      phone_verified: true,
      kyc_status: 'approved',
      has_passkey: true,
      is_complete: true,
    }),
  ),

  http.get(`${API_URL}/v1/auth/totp/status`, () => HttpResponse.json({ enabled: false })),

  http.post(`${API_URL}/v1/auth/totp/setup`, () =>
    HttpResponse.json({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri: 'otpauth://totp/QREW:user@example.com?secret=JBSWY3DPEHPK3PXP',
      backup_codes: ['1111-1111', '2222-2222'],
    }),
  ),

  http.post(`${API_URL}/v1/auth/totp/confirm`, () =>
    HttpResponse.json({ message: 'Two-factor authentication enabled.' }),
  ),

  http.post(`${API_URL}/v1/auth/totp/disable`, () =>
    HttpResponse.json({ message: 'Two-factor authentication disabled.' }),
  ),

  http.get(`${API_URL}/v1/auth/devices`, () =>
    HttpResponse.json({
      items: [
        {
          id: 'device-1',
          name: 'Pixel 8',
          last_seen_at: '2026-08-20T10:00:00Z',
          created_at: '2026-07-01T10:00:00Z',
          is_current: true,
        },
        {
          id: 'device-2',
          name: 'iPhone 15',
          last_seen_at: '2026-08-18T10:00:00Z',
          created_at: '2026-07-05T10:00:00Z',
          is_current: false,
        },
      ],
      next_cursor: null,
    }),
  ),

  http.post(`${API_URL}/v1/auth/devices/:deviceId/revoke`, () =>
    HttpResponse.json({ message: 'Device removed.' }),
  ),

  http.post(`${API_URL}/v1/auth/devices/revoke-all`, () =>
    HttpResponse.json({ message: 'All devices removed.' }),
  ),

  http.get(`${API_URL}/v1/auth/profile/audit`, () =>
    HttpResponse.json({
      items: [
        {
          id: '11111111-1111-1111-1111-111111111111',
          action: 'login',
          entity_type: 'user',
          summary: 'Signed in',
          ip_address: '203.0.113.5',
          device_fingerprint_hash: null,
          created_at: '2026-08-20T10:00:00Z',
        },
      ],
      next_cursor: null,
    }),
  ),

  http.get(`${API_URL}/v1/admin/users/search`, () =>
    HttpResponse.json({ items: [], next_cursor: null }),
  ),

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
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0',
          device_fingerprint: null,
          created_at: '2026-07-01T10:00:00Z',
          last_used_at: '2026-07-06T10:00:00Z',
          is_current: false,
          location: null,
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
