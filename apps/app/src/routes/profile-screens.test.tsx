// tests profile screens
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, declaredPaths, renderRoute } from '@/test/router'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const PATHS = declaredPaths({ under: '/profile' })

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
