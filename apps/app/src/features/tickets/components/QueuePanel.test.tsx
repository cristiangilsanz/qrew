// tests queue panel
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { server } from '@/test/server'

import { QueuePanel } from './QueuePanel'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  // renders the toaster component
  Toaster: () => null,
}))

// implements render panel
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
  it('shows loading spinner while joining', () => {
    renderPanel()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('shows queue position after joining', async () => {
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  it('shows error toast when join fails', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('http://localhost:8000/api/sales/v1/events/:eventId/queue/join', () =>
        HttpResponse.json({ detail: 'Event not found' }, { status: 404 }),
      ),
    )
    renderPanel()
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled()
    })
  })
})
