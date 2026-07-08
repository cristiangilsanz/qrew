import { render, screen } from '@testing-library/react'
import React from 'react'
import { describe, expect, it, vi } from 'vitest'

import { type EventDetail } from '../api'
import { EventDetailCard } from './EventDetailCard'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    Link: ({
      children,
      ...props
    }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { children?: React.ReactNode }) => (
      <a {...props}>{children}</a>
    ),
  }
})

const mockEvent: EventDetail = {
  id: 'event-1',
  name: 'Summer Fest',
  description: 'The biggest summer festival in Barcelona.',
  starts_at: '2026-08-15T20:00:00Z',
  ends_at: '2026-08-15T23:59:00Z',
  sale_starts_at: '2026-07-01T00:00:00Z',
  sale_ends_at: '2026-08-14T23:59:00Z',
  max_tickets_per_user: 4,
  queue_required: false,
  published_at: '2026-07-01T00:00:00Z',
  organisation: { id: 'org-1', slug: 'qrew-events', name: 'Qrew Events', description: null },
  venue: {
    id: 'venue-1',
    name: 'Parc de la Ciutadella',
    city: 'Barcelona',
    country: 'ES',
    latitude: 41.386,
    longitude: 2.186,
    geofence_radius_m: 200,
    timezone: 'Europe/Madrid',
  },
  ticket_types: [
    {
      id: 'tt-1',
      name: 'General',
      description: null,
      capacity: 500,
      reserved_count: 120,
      available: 380,
      price_cents: 2500,
      currency: 'EUR',
      position: 1,
    },
    {
      id: 'tt-2',
      name: 'VIP',
      description: 'Front row access',
      capacity: 50,
      reserved_count: 50,
      available: 0,
      price_cents: 7500,
      currency: 'EUR',
      position: 2,
    },
  ],
}

describe('EventDetailCard', () => {
  it('renders event name', () => {
    render(<EventDetailCard event={mockEvent} />)
    expect(screen.getByText('Summer Fest')).toBeInTheDocument()
  })

  it('renders event description', () => {
    render(<EventDetailCard event={mockEvent} />)
    expect(screen.getByText('The biggest summer festival in Barcelona.')).toBeInTheDocument()
  })

  it('renders venue city', () => {
    render(<EventDetailCard event={mockEvent} />)
    expect(screen.getByText(/Parc de la Ciutadella/)).toBeInTheDocument()
  })

  it('renders ticket type names and prices', () => {
    render(<EventDetailCard event={mockEvent} />)
    expect(screen.getByText('General')).toBeInTheDocument()
    expect(screen.getByText('25.00 EUR')).toBeInTheDocument()
    expect(screen.getByText('VIP')).toBeInTheDocument()
    expect(screen.getByText('75.00 EUR')).toBeInTheDocument()
  })

  it('shows sold out badge for unavailable ticket types', () => {
    render(<EventDetailCard event={mockEvent} />)
    expect(screen.getByText(/sold out/i)).toBeInTheDocument()
  })

  it('shows available count for available ticket types', () => {
    render(<EventDetailCard event={mockEvent} />)
    expect(screen.getByText(/380/)).toBeInTheDocument()
  })
})
