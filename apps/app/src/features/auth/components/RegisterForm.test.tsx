// tests register form
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { RegisterForm } from './RegisterForm'

const mockNavigate = vi.fn()

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  // renders the toaster component
  Toaster: () => null,
}))

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    // provides use navigate
    useNavigate: () => mockNavigate,
    // renders the link component
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('@marsidev/react-turnstile', async () => {
  const { useEffect } = await import('react')
  return {
    // renders the turnstile component
    Turnstile: ({ onSuccess }: { onSuccess: (token: string) => void }) => {
      useEffect(() => {
        onSuccess('mock-captcha-token')
      }, [onSuccess])
      return null
    },
  }
})

// implements render register form
function renderRegisterForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RegisterForm />
    </QueryClientProvider>,
  )
}

// implements fill valid form
async function fillValidForm() {
  await userEvent.type(screen.getByLabelText(/full name/i), 'Jane Doe')
  await userEvent.type(screen.getByLabelText(/email/i), 'jane@example.com')
  await userEvent.type(screen.getByLabelText(/phone number/i), '+34612345678')
  await userEvent.type(screen.getByLabelText(/password/i), 'securepass1')
  await userEvent.click(screen.getByLabelText(/terms/i))
}

describe('RegisterForm', () => {
  it('renders all required fields', () => {
    renderRegisterForm()
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/terms/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('shows validation errors on empty submit', async () => {
    renderRegisterForm()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create account/i })).not.toBeDisabled()
    })
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => {
      expect(document.querySelectorAll('[id$="-form-item-message"]').length).toBeGreaterThan(0)
    })
  })

  it('shows toast and hands the new account to the setup wizard', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8000/api/identity/v1/auth/login', () =>
        HttpResponse.json({
          access_token: 'setup-token',
          refresh_token: null,
          token_type: 'bearer',
          setup_required: true,
          totp_required: false,
          password_compromised: false,
        }),
      ),
    )
    renderRegisterForm()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create account/i })).not.toBeDisabled()
    })
    await fillValidForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Account created.')
      expect(mockNavigate).toHaveBeenCalledWith({ to: '/setup' })
    })
  })

  it('calls toast.error when registration fails', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8000/api/identity/v1/auth/registration/', () =>
        HttpResponse.json({ detail: 'Email already registered.' }, { status: 409 }),
      ),
    )

    renderRegisterForm()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create account/i })).not.toBeDisabled()
    })
    await fillValidForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Email already registered.')
    })
  })
})
