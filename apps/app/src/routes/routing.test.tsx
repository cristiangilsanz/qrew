// tests routing
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { currentPath, renderRoute } from '@/test/router'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

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

describe('route guards', () => {
  it('sends an anonymous visitor from the root to the login screen', async () => {
    signOut()
    const { router } = await renderRoute('/')
    expect(currentPath(router)).toBe('/login')
  })

  it('sends a signed-in visitor from the root to the home screen', async () => {
    signIn()
    const { router } = await renderRoute('/')
    expect(currentPath(router)).toBe('/home')
    signOut()
  })

  it('refuses an application screen to an anonymous visitor', async () => {
    signOut()
    const { router } = await renderRoute('/profile')
    expect(currentPath(router)).toBe('/login')
  })

  it('refuses the login screen to a signed-in visitor', async () => {
    signIn()
    const { router } = await renderRoute('/login')
    expect(currentPath(router)).toBe('/home')
    signOut()
  })

  it('answers an unknown path with the not-found screen', async () => {
    signIn()
    const { router } = await renderRoute('/there-is-nothing-here')
    expect(currentPath(router)).toBe('/there-is-nothing-here')
    signOut()
  })
})
