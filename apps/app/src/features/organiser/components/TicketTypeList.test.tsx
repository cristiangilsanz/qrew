import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { TicketTypeList } from './TicketTypeList'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

function renderList(eventId = 'event-1') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <TicketTypeList eventId={eventId} />
    </QueryClientProvider>,
  )
}

describe('TicketTypeList', () => {
  it('renders ticket type from mock data', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText('General')).toBeInTheDocument()
    })
    expect(screen.getByText(/15\.00 EUR/)).toBeInTheDocument()
  })

  it('shows the create form when "Add ticket type" is clicked', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText('General')).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('button', { name: /add ticket type/i }))
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
  })
})
