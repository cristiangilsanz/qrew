// tests management screens
import { waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'
import { server } from '@/test/server'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const IDENTITY_URL = 'http://localhost:8000/api/identity'
const CATALOG_URL = 'http://localhost:8000/api/catalog'

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

// implements sign in
function signIn() {
  useAuthStore.setState({
    accessToken: 'header.payload.signature',
    refreshToken: 'refresh',
    isAuthenticated: true,
  })
}

// implements sign out
function signOut() {
  useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
}

// implements as admin
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
    '/management/org-1/collaborators',
    '/management/org-1/collaborators/new',
    '/management/org-1/venues/new',
  ]

  it.each(PATHS)('renders %s for an administrator', async (path) => {
    signIn()
    asAdmin()
    const { router, container, queryClient } = await renderRoute(path)
    expect(currentPath(router)).toBe(path)
    // the screen only reaches its loaded state once every query it fires has settled
    await waitFor(() => expect(queryClient.isFetching()).toBe(0), { timeout: 5000 })
    expect(container.textContent?.trim()).not.toBe('')
    signOut()
  })

  it('sends a visitor who belongs to no organisation back home', async () => {
    signIn()
    server.use(
      http.get(`${IDENTITY_URL}/v1/auth/profile/me`, () =>
        HttpResponse.json({ ...PROFILE, is_admin: false }),
      ),
      http.get(`${CATALOG_URL}/v1/organisations`, () =>
        HttpResponse.json({ items: [], next_cursor: null }),
      ),
    )
    const { router } = await renderRoute('/management')
    await waitFor(() => expect(currentPath(router)).toBe('/home'))
    signOut()
  })

  it('lets a collaborator without administration rights in', async () => {
    signIn()
    server.use(
      http.get(`${IDENTITY_URL}/v1/auth/profile/me`, () =>
        HttpResponse.json({ ...PROFILE, is_admin: false }),
      ),
    )
    const { router } = await renderRoute('/management')
    await waitFor(() => expect(currentPath(router)).toBe('/management'))
    signOut()
  })
})
