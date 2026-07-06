import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { type EventSummary } from '../api'
import { EventCard } from './EventCard'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

const mockEvent: EventSummary = {
  id: 'event-1',
  name: 'Summer Fest',
  organiser_name: 'Qrew Events',
  venue_city: 'Barcelona',
  starts_at: '2026-08-15T20:00:00Z',
  rank: null,
}

describe('EventCard', () => {
  it('renders event name', () => {
    render(<EventCard event={mockEvent} />)
    expect(screen.getByText('Summer Fest')).toBeInTheDocument()
  })

  it('renders organiser name', () => {
    render(<EventCard event={mockEvent} />)
    expect(screen.getByText('Qrew Events')).toBeInTheDocument()
  })

  it('renders venue city', () => {
    render(<EventCard event={mockEvent} />)
    expect(screen.getByText(/Barcelona/)).toBeInTheDocument()
  })

  it('renders event date', () => {
    render(<EventCard event={mockEvent} />)
    expect(screen.getByText(/2026/)).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<EventCard event={mockEvent} onClick={onClick} />)
    screen.getByRole('article').click()
    expect(onClick).toHaveBeenCalled()
  })
})
