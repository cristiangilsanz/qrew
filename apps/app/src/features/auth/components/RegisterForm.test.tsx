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
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => {
      expect(document.querySelectorAll('[id$="-form-item-message"]').length).toBeGreaterThan(0)
    })
  })

  it('shows toast and navigates to /login on success', async () => {
    const { toast } = await import('sonner')
    renderRegisterForm()
    await fillValidForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Check your email'))
      expect(mockNavigate).toHaveBeenCalledWith({ to: '/login' })
    })
  })

  it('calls toast.error when registration fails', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8001/v1/auth/registration/', () =>
        HttpResponse.json({ detail: 'Email already registered' }, { status: 409 }),
      ),
    )

    renderRegisterForm()
    await fillValidForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Email already registered')
    })
  })
})
