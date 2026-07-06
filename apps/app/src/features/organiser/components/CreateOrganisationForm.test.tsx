import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { CreateOrganisationForm } from './CreateOrganisationForm'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return { ...actual, useNavigate: () => vi.fn(), Link: actual.Link }
})

function renderForm(onSuccess?: (id: string) => void) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <CreateOrganisationForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

describe('CreateOrganisationForm', () => {
  it('renders slug and name fields', () => {
    renderForm()
    expect(screen.getByLabelText(/slug/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^name/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /new organisation/i })).toBeInTheDocument()
  })

  it('shows toast.success on successful create', async () => {
    const { toast } = await import('sonner')
    renderForm()

    await userEvent.type(screen.getByLabelText(/slug/i), 'my-org')
    await userEvent.type(screen.getByLabelText(/^name/i), 'My Org')
    await userEvent.click(screen.getByRole('button', { name: /new organisation/i }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Organisation created.')
    })
  })

  it('shows toast.error on slug conflict (409)', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8002/v1/organisations', () =>
        HttpResponse.json({ detail: 'Slug already taken' }, { status: 409 }),
      ),
    )

    renderForm()

    await userEvent.type(screen.getByLabelText(/slug/i), 'taken-org')
    await userEvent.type(screen.getByLabelText(/^name/i), 'Taken Org')
    await userEvent.click(screen.getByRole('button', { name: /new organisation/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Slug already taken')
    })
  })
})
