// implements entry
import { http, HttpResponse } from 'msw'

const ENTRY_URL = 'http://localhost:8000/api/entry'

export const entryHandlers = [
  http.get(`${ENTRY_URL}/v1/events/:eventId/entry-stats`, () =>
    HttpResponse.json({
      issued: 120,
      admitted: 80,
      denied: 4,
      last_admission_at: new Date().toISOString(),
    }),
  ),

  http.post(`${ENTRY_URL}/v1/scanners/for-event/:eventId`, () =>
    HttpResponse.json({ scanner_token: 'mock-scanner-token' }),
  ),
]
