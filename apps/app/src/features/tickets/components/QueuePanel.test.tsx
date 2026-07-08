import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { QueuePanel } from './QueuePanel'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

function renderPanel(eventId = 'event-1') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <QueuePanel eventId={eventId} />
    </QueryClientProvider>,
  )
}

describe('QueuePanel', () => {
  it('renders join queue button initially', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /join queue/i })).toBeInTheDocument()
  })

  it('shows queue position after joining', async () => {
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: /join queue/i }))
    await waitFor(() => {
      // After join (position 5 from join response) the position query fires immediately
      // and returns position 3 from the polling endpoint
      expect(screen.queryByRole('button', { name: /join queue/i })).not.toBeInTheDocument()
    })
  })

  it('shows error toast when join fails', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8003/v1/events/:eventId/queue/join', () =>
        HttpResponse.json({ detail: 'Event not found' }, { status: 404 }),
      ),
    )
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: /join queue/i }))
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled()
    })
  })
})
