import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const PATHS = [
  '/home',
  '/events',
  '/events/event-1',
  '/tickets',
  '/tickets/ticket-1',
  '/market',
  '/market/claims',
  '/market/my-listings',
  '/market/waitlists',
  '/reservations/res-1',
  '/events/event-1/queue',
  '/events/event-1/checkout',
  '/market/assignments/assignment-1',
]

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
    const { router, container } = await renderRoute(path)
    expect(currentPath(router)).toBe(path)
    expect(container.textContent?.trim()).not.toBe('')
    useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
  })
})
