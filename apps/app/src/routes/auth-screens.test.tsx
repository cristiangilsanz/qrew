// tests auth screens
import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const PATHS = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-totp']

describe('authentication screens', () => {
  it.each(PATHS)('renders %s for an anonymous visitor', async (path) => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
    const { router, container } = await renderRoute(path)
    expect(currentPath(router)).toBe(path)
    expect(container.textContent?.trim()).not.toBe('')
  })

  it('refuses the onboarding screen when no setup is pending', async () => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isSetupPending: false,
    })
    const { router } = await renderRoute('/setup')
    expect(currentPath(router)).toBe('/login')
  })

  it('serves the onboarding screen while a setup is pending', async () => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isSetupPending: true,
    })
    const { router } = await renderRoute('/setup')
    expect(currentPath(router)).toBe('/setup')
    useAuthStore.setState({ isSetupPending: false })
  })

  it('offers a way into the login screen and out to registration', async () => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
    await renderRoute('/login')
    expect(screen.getAllByRole('button').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /account|cuenta|regist/i })).toBeInTheDocument()
  })
})
