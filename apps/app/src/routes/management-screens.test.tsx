import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'
import { server } from '@/test/server'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const IDENTITY_URL = 'http://localhost:8000/api/identity'

const PROFILE = {
  id: 'mock-user-id',
  email: 'user@example.com',
  full_name: 'Test User',
  phone_number: '+34600000000',
  kyc_status: 'approved',
  email_verified: true,
  phone_verified: true,
  created_at: '2026-01-01T00:00:00Z',
}

function signIn() {
  useAuthStore.setState({
    accessToken: 'header.payload.signature',
    refreshToken: 'refresh',
    isAuthenticated: true,
  })
}

function signOut() {
  useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
}

function asAdmin() {
  server.use(
    http.get(`${IDENTITY_URL}/v1/auth/profile/me`, () =>
      HttpResponse.json({ ...PROFILE, is_admin: true }),
    ),
  )
}

describe('management screens', () => {
  const PATHS = [
    '/management',
    '/management/new',
    '/management/org-1',
    '/management/org-1/events',
    '/management/org-1/events/new',
    '/management/org-1/events/event-1',
    '/management/org-1/events/event-1/edit',
    '/management/org-1/events/event-1/stats',
    '/management/org-1/events/event-1/tickets',
    '/management/org-1/events/event-1/scan',
    '/management/org-1/members',
    '/management/org-1/members/new',
    '/management/org-1/venues/new',
  ]

  it.each(PATHS)('renders %s for an administrator', async (path) => {
    signIn()
    asAdmin()
    const { router, container } = await renderRoute(path)
    expect(currentPath(router)).toBe(path)
    expect(container.textContent?.trim()).not.toBe('')
    signOut()
  })

  it('sends a visitor without administration rights back home', async () => {
    signIn()
    server.use(
      http.get(`${IDENTITY_URL}/v1/auth/profile/me`, () =>
        HttpResponse.json({ ...PROFILE, is_admin: false }),
      ),
    )
    const { router } = await renderRoute('/management')
    expect(currentPath(router)).toBe('/home')
    signOut()
  })
})
