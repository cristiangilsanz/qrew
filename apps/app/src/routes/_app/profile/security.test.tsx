// tests security screen
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { renderRoute } from '@/test/router'
import { server } from '@/test/server'

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const API = 'http://localhost:8000/api/identity'

// implements sign in
function signIn() {
  useAuthStore.setState({
    accessToken: 'header.payload.signature',
    refreshToken: 'refresh',
    isAuthenticated: true,
  })
}

// implements open security
async function openSecurity() {
  signIn()
  const rendered = await renderRoute('/profile/security')
  useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
  return rendered
}

describe('security screen', () => {
  it('lists the sections a user can act on', async () => {
    await openSecurity()
    expect(screen.getByRole('heading', { name: /privacy & security/i })).toBeInTheDocument()
    expect(screen.getByText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByText(/two-factor authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/trusted devices/i)).toBeInTheDocument()
    expect(screen.getByText(/recent activity/i)).toBeInTheDocument()
  })

  it('unfolds the password form on demand', async () => {
    await openSecurity()
    await userEvent.click(screen.getByText(/^password$/i))
    await waitFor(() => {
      expect(screen.getByLabelText(/current password/i)).toBeInTheDocument()
    })
  })

  it('walks the second factor from the key to the confirmation', async () => {
    await openSecurity()
    await userEvent.click(await screen.findByRole('button', { name: /set up/i }))
    await waitFor(() => {
      expect(screen.getByText(/scan this qr code/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/JBSWY3DPEHPK3PXP/)).toBeInTheDocument()
  })

  it('offers to disable the second factor when it is already on', async () => {
    server.use(http.get(`${API}/v1/auth/totp/status`, () => HttpResponse.json({ enabled: true })))
    await openSecurity()
    const disable = await screen.findByRole('button', { name: /disable/i })
    await userEvent.click(disable)
    await waitFor(() => {
      expect(screen.getByText(/enter your authenticator code/i)).toBeInTheDocument()
    })
  })

  it('shows the device the account trusts', async () => {
    await openSecurity()
    await userEvent.click(screen.getByText(/trusted devices/i))
    await waitFor(() => {
      expect(screen.getByText(/pixel 8/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/this device/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument()
  })

  it('offers recovery when the trusted device is another one', async () => {
    server.use(
      http.get(`${API}/v1/auth/devices`, () =>
        HttpResponse.json({
          items: [
            {
              id: 'device-1',
              name: 'Pixel 8',
              last_seen_at: '2026-08-20T10:00:00Z',
              created_at: '2026-07-01T10:00:00Z',
              is_current: false,
            },
          ],
          next_cursor: null,
        }),
      ),
    )
    await openSecurity()
    await userEvent.click(screen.getByText(/trusted devices/i))
    const link = await screen.findByRole('link', { name: /lost that device/i })
    expect(link).toHaveAttribute('href', '/profile/recover-device')
  })

  it('shows the recent activity of the account', async () => {
    await openSecurity()
    await userEvent.click(screen.getByText(/recent activity/i))
    await waitFor(() => {
      expect(screen.getByText(/signed in/i)).toBeInTheDocument()
    })
  })

  it('reports an empty activity log as such', async () => {
    server.use(
      http.get(`${API}/v1/auth/profile/audit`, () =>
        HttpResponse.json({ items: [], next_cursor: null }),
      ),
    )
    await openSecurity()
    await userEvent.click(screen.getByText(/recent activity/i))
    await waitFor(() => {
      expect(screen.getByText(/no activity/i)).toBeInTheDocument()
    })
  })
})
