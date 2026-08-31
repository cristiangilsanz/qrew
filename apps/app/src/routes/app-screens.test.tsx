// tests app screens
import { waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const PATHS = [
  '/home',
  '/events',
  '/events/event-1',
  '/tickets',
  '/tickets/ticket-1',
  '/market',
  '/market/offers',
  '/market/on-sale',
  '/market/waitlists',
  '/reservations/res-1',
  '/events/event-1/queue',
  '/events/event-1/checkout',
  '/market/offers/assignment-1',
  '/profile',
  '/profile/about',
  '/profile/help',
  '/profile/passkeys',
  '/profile/account',
  '/profile/security',
]

// implements sign in
function signIn() {
  useAuthStore.setState({
    accessToken: 'header.payload.signature',
    refreshToken: 'refresh',
    isAuthenticated: true,
  })
}

describe('application screens', () => {
  it.each(PATHS)('renders %s for a signed-in visitor', async (path) => {
    signIn()
    const { router, container, queryClient } = await renderRoute(path)
    expect(currentPath(router)).toBe(path)
    // the screen only reaches its loaded state once every query it fires has settled
    await waitFor(() => expect(queryClient.isFetching()).toBe(0), { timeout: 5000 })
    expect(container.textContent?.trim()).not.toBe('')
    useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
  })
})
