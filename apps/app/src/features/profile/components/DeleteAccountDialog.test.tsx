import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { DeleteAccountDialog } from './DeleteAccountDialog'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const ENDPOINT = 'http://localhost:8000/api/identity/v1/auth/account/delete'

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <DeleteAccountDialog />
    </QueryClientProvider>,
  )
}

async function openAndWaitOutTheDelay() {
  await userEvent.click(screen.getByRole('button', { name: /delete my account/i }))
  await act(async () => {
    vi.advanceTimersByTime(10_000)
  })
}

describe('DeleteAccountDialog', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows only the entry button until it is pressed', () => {
    renderDialog()
    expect(screen.getByRole('button', { name: /delete my account/i })).toBeInTheDocument()
    expect(screen.queryByLabelText(/current password/i)).not.toBeInTheDocument()
  })

  it('holds the confirmation back while the countdown runs', async () => {
    renderDialog()
    await userEvent.click(screen.getByRole('button', { name: /delete my account/i }))
    expect(screen.getByRole('button', { name: /wait/i })).toBeDisabled()
  })

  it('releases the confirmation once the countdown ends', async () => {
    renderDialog()
    await openAndWaitOutTheDelay()
    expect(screen.getByRole('button', { name: /delete account/i })).toBeEnabled()
  })

  it('sends nothing when the user goes back', async () => {
    let calls = 0
    server.use(
      http.post(ENDPOINT, () => {
        calls += 1
        return HttpResponse.json({ message: 'Account deleted.' })
      }),
    )
    renderDialog()
    await openAndWaitOutTheDelay()
    await userEvent.type(screen.getByLabelText(/current password/i), 'StrongP@ss1!')
    await userEvent.click(screen.getByRole('button', { name: /go back/i }))
    await act(async () => {
      vi.advanceTimersByTime(500)
    })
    expect(calls).toBe(0)
  })

  it('reports the rejection when the password does not match', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ detail: { message: 'Incorrect password' } }, { status: 400 }),
      ),
    )
    renderDialog()
    await openAndWaitOutTheDelay()
    await userEvent.type(screen.getByLabelText(/current password/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /delete account/i }))
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
  })
})
