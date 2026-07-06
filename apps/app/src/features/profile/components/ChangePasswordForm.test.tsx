import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { ChangePasswordForm } from './ChangePasswordForm'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ChangePasswordForm />
    </QueryClientProvider>,
  )
}

describe('ChangePasswordForm', () => {
  it('renders current and new password fields', () => {
    renderForm()
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /update password/i })).toBeInTheDocument()
  })

  it('shows toast.success on successful password change', async () => {
    const { toast } = await import('sonner')
    renderForm()

    await userEvent.type(screen.getByLabelText(/current password/i), 'oldpass123')
    await userEvent.type(screen.getByLabelText(/new password/i), 'newpass456')
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Password updated.')
    })
  })

  it('shows toast.error when change-password returns 400', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8001/v1/auth/account/change-password', () =>
        HttpResponse.json({ detail: 'Incorrect current password' }, { status: 400 }),
      ),
    )

    renderForm()

    await userEvent.type(screen.getByLabelText(/current password/i), 'wrongpass')
    await userEvent.type(screen.getByLabelText(/new password/i), 'newpass456')
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Incorrect current password')
    })
  })
})
