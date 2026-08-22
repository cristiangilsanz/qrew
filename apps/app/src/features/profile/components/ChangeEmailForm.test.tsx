import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { ChangeEmailForm } from './ChangeEmailForm'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const ENDPOINT = 'http://localhost:8000/api/identity/v1/auth/account/change-email'

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ChangeEmailForm />
    </QueryClientProvider>,
  )
}

describe('ChangeEmailForm', () => {
  it('asks for the new address and for the password', () => {
    renderForm()
    expect(screen.getByText(/change email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/new email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password confirmation/i)).toBeInTheDocument()
  })

  it('refuses an address that is not one', async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/new email/i), 'not-an-address')
    await userEvent.type(screen.getByLabelText(/password confirmation/i), 'StrongP@ss1!')
    await userEvent.click(screen.getByRole('button', { name: /send confirmation link/i }))
    await waitFor(() => {
      expect(screen.queryByText(/confirmation link sent/i)).not.toBeInTheDocument()
    })
    expect(screen.getByLabelText(/new email/i)).toBeInTheDocument()
  })

  it('announces the link once the change is accepted', async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/new email/i), 'new@example.com')
    await userEvent.type(screen.getByLabelText(/password confirmation/i), 'StrongP@ss1!')
    await userEvent.click(screen.getByRole('button', { name: /send confirmation link/i }))
    await waitFor(() => {
      expect(screen.getByText(/confirmation link sent/i)).toBeInTheDocument()
    })
  })

  it('lets the user return to the form after sending the link', async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/new email/i), 'new@example.com')
    await userEvent.type(screen.getByLabelText(/password confirmation/i), 'StrongP@ss1!')
    await userEvent.click(screen.getByRole('button', { name: /send confirmation link/i }))
    await waitFor(() => expect(screen.getByText(/confirmation link sent/i)).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByLabelText(/new email/i)).toBeInTheDocument()
  })

  it('reports the rejection when the password does not match', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ detail: { message: 'Incorrect password' } }, { status: 400 }),
      ),
    )
    renderForm()
    await userEvent.type(screen.getByLabelText(/new email/i), 'new@example.com')
    await userEvent.type(screen.getByLabelText(/password confirmation/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /send confirmation link/i }))
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
  })
})
