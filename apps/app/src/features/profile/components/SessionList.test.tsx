import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { SessionList } from './SessionList'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

function renderList() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <SessionList />
    </QueryClientProvider>,
  )
}

describe('SessionList', () => {
  it('renders session user_agent', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText('Chrome on Windows')).toBeInTheDocument()
    })
  })

  it('calls revoke endpoint when revoke button is clicked', async () => {
    let revokeCalled = false
    server.use(
      http.delete('http://localhost:8000/api/identity/v1/auth/sessions/:jti', () => {
        revokeCalled = true
        return new HttpResponse(null, { status: 204 })
      }),
    )

    renderList()
    await waitFor(() => screen.getByText('Chrome on Windows'))

    await userEvent.click(screen.getAllByRole('button')[0])

    await waitFor(() => screen.getByText('Revoke'))
    await userEvent.click(screen.getByText('Revoke'))

    await waitFor(() => {
      expect(revokeCalled).toBe(true)
    })
  })
})
