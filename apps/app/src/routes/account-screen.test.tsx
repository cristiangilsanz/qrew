import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { renderRoute } from '@/test/router'
import { server } from '@/test/server'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const API = 'http://localhost:8000/api/identity'

const PROFILE = {
  id: 'mock-user-id',
  email: 'user@example.com',
  full_name: 'Test User',
  phone_number: '+34600000000',
  kyc_status: 'approved',
  email_verified: true,
  phone_verified: true,
  created_at: '2026-01-15T00:00:00Z',
}

async function openAccount() {
  useAuthStore.setState({
    accessToken: 'header.payload.signature',
    refreshToken: 'refresh',
    isAuthenticated: true,
  })
  const rendered = await renderRoute('/profile/account')
  useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false })
  return rendered
}

describe('account screen', () => {
  it('states what the account holds', async () => {
    await openAccount()
    await waitFor(() => expect(screen.getByText('Test User')).toBeInTheDocument())
    expect(screen.getByText('user@example.com')).toBeInTheDocument()
    expect(screen.getByText('+34600000000')).toBeInTheDocument()
    expect(screen.getByText(/january/i)).toBeInTheDocument()
  })

  it('unfolds the change of address and folds it back', async () => {
    await openAccount()
    await waitFor(() => expect(screen.getByText('user@example.com')).toBeInTheDocument())
    await userEvent.click(screen.getByText('user@example.com'))
    await waitFor(() => expect(screen.getByLabelText(/new email/i)).toBeInTheDocument())
    await userEvent.click(screen.getByText('user@example.com'))
    await waitFor(() => {
      expect(screen.queryByLabelText(/new email/i)).not.toBeInTheDocument()
    })
  })

  it('unfolds the change of number', async () => {
    await openAccount()
    await waitFor(() => expect(screen.getByText('+34600000000')).toBeInTheDocument())
    await userEvent.click(screen.getByText('+34600000000'))
    await waitFor(() => {
      expect(screen.getByLabelText(/new phone number/i)).toBeInTheDocument()
    })
  })

  it('offers the document upload when the identity is not yet verified', async () => {
    server.use(
      http.get(`${API}/v1/auth/profile/me`, () =>
        HttpResponse.json({ ...PROFILE, kyc_status: 'not_submitted' }),
      ),
    )
    await openAccount()
    await waitFor(() => expect(screen.getByText('Test User')).toBeInTheDocument())
    expect(screen.getByText(/not submitted|pending|identity/i)).toBeInTheDocument()
  })

  it('shows the placeholders while the account is still loading', async () => {
    server.use(
      http.get(`${API}/v1/auth/profile/me`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50))
        return HttpResponse.json(PROFILE)
      }),
    )
    const { container } = await openAccount()
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })
})
