import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const PATHS = [
  '/profile',
  '/profile/about',
  '/profile/help',
  '/profile/terms',
  '/profile/privacy',
  '/profile/passkeys',
  '/profile/account',
  '/profile/security',
]

describe('profile screens', () => {
  it.each(PATHS)('renders %s for a signed-in visitor', async (path) => {
    useAuthStore.setState({
      accessToken: 'header.payload.signature',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })
    const { router, container } = await renderRoute(path)
    expect(currentPath(router)).toBe(path)
    expect(container.textContent?.trim()).not.toBe('')
    useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
  })
})
