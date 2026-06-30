import { http, HttpResponse } from 'msw'

export const handlers = [
  http.post(`${import.meta.env.VITE_API_URL}/auth/login`, () => {
    return HttpResponse.json({ access_token: 'mock-token' })
  }),
]
