import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { LoginForm } from './LoginForm'

const mockNavigate = vi.fn()

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

function renderLoginForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <LoginForm />
    </QueryClientProvider>,
  )
}

describe('LoginForm', () => {
  it('renders email and password fields', () => {
    renderLoginForm()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows validation errors on empty submit', async () => {
    renderLoginForm()
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(document.querySelectorAll('[id$="-form-item-message"]').length).toBeGreaterThan(0)
    })
  })

  it('navigates to /events on successful login', async () => {
    renderLoginForm()

    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith({ to: '/events' })
    })
  })

  it('calls toast.error when login fails', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8001/v1/auth/login', () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 }),
      ),
    )

    renderLoginForm()

    await userEvent.type(screen.getByLabelText(/email/i), 'bad@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpass')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid credentials')
    })
  })
})
