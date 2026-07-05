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
]
