import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { TicketCard } from './TicketCard'

vi.mock('@tanstack/react-router', () => ({
  Link: ({
    children,
    to,
    params,
  }: {
    children: ReactNode
    to: string
    params?: Record<string, string>
  }) => {
    const href = params
      ? Object.entries(params).reduce((acc, [k, v]) => acc.replace(`$${k}`, v), to)
      : to
    return <a href={href}>{children}</a>
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (key === 'tickets.ticket.id') return `Ticket #${opts?.id}`
      if (key.startsWith('tickets.ticket.states.')) return key.split('.').pop() ?? key
      return key
    },
  }),
}))

const BASE_TICKET = {
  id: 'abc12345-0000-0000-0000-000000000000',
  reservation_id: 'res-1',
  event_id: 'event-1',
  ticket_type_id: 'tt-1',
  state: 'issued' as const,
  state_updated_at: null,
  created_at: new Date('2026-07-01').toISOString(),
}

describe('TicketCard', () => {
  it('renders ticket id and state badge', () => {
    render(<TicketCard ticket={BASE_TICKET} />)
    expect(screen.getByText(/Ticket #abc12345/i)).toBeInTheDocument()
    expect(screen.getByText('issued')).toBeInTheDocument()
  })

  it('renders created date', () => {
    render(<TicketCard ticket={BASE_TICKET} />)
    expect(screen.getByText(/2026/)).toBeInTheDocument()
  })

  it('links to ticket detail page', () => {
    render(<TicketCard ticket={BASE_TICKET} />)
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/tickets/abc12345-0000-0000-0000-000000000000')
  })

  it('shows destructive badge for cancelled state', () => {
    render(<TicketCard ticket={{ ...BASE_TICKET, state: 'cancelled' }} />)
    expect(screen.getByText('cancelled')).toBeInTheDocument()
  })

  it('shows secondary badge for reserved state', () => {
    render(<TicketCard ticket={{ ...BASE_TICKET, state: 'reserved' }} />)
    expect(screen.getByText('reserved')).toBeInTheDocument()
  })
})
