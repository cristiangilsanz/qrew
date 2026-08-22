import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { ChangePhoneForm } from './ChangePhoneForm'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const API = 'http://localhost:8000/api/identity'

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ChangePhoneForm />
    </QueryClientProvider>,
  )
}

async function requestTheChange() {
  await userEvent.type(screen.getByLabelText(/new phone number/i), '+34611222333')
  await userEvent.type(screen.getByLabelText(/password confirmation/i), 'StrongP@ss1!')
  await userEvent.click(screen.getByRole('button', { name: /send verification code/i }))
}

describe('ChangePhoneForm', () => {
  it('asks for the new number and for the password', () => {
    renderForm()
    expect(screen.getByLabelText(/new phone number/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password confirmation/i)).toBeInTheDocument()
  })

  it('moves on to the code once the number is accepted', async () => {
    renderForm()
    await requestTheChange()
    await waitFor(() => {
      expect(screen.getByText(/enter the code sent to your new number/i)).toBeInTheDocument()
    })
    expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
  })

  it('returns to the number when the user cancels the code', async () => {
    renderForm()
    await requestTheChange()
    await waitFor(() => expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.getByLabelText(/new phone number/i)).toBeInTheDocument()
  })

  it('closes the change once the code is confirmed', async () => {
    server.use(
      http.post(`${API}/v1/auth/account/confirm-phone-change`, () =>
        HttpResponse.json({ message: 'Phone number updated.' }),
      ),
    )
    renderForm()
    await requestTheChange()
    await waitFor(() => expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument())
    await userEvent.type(screen.getByLabelText(/verification code/i), '123456')
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }))
    await waitFor(() => {
      expect(screen.getByLabelText(/new phone number/i)).toBeInTheDocument()
    })
  })

  it('reports the rejection when the number is already taken', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post(`${API}/v1/auth/account/change-phone`, () =>
        HttpResponse.json({ detail: { message: 'Phone already registered' } }, { status: 409 }),
      ),
    )
    renderForm()
    await requestTheChange()
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
  })
})
