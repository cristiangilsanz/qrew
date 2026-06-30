import { http, HttpResponse } from 'msw'

const API_URL = 'http://localhost:8001'

export const authHandlers = [
  http.post(`${API_URL}/auth/login`, () => {
    return HttpResponse.json({ access_token: 'mock-token' })
  }),
]
