import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { OrgEvent } from '../api'
import { EventActions } from './EventActions'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

vi.mock('../hooks/usePublishEvent', () => ({
  usePublishEvent: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('../hooks/useStartEvent', () => ({
  useStartEvent: () => ({ mutate: vi.fn(), isPending: false }),
}))

function makeEvent(status: OrgEvent['status']): OrgEvent {
  return {
    id: 'event-1',
    organisation_id: 'org-1',
    venue_id: 'venue-1',
    name: 'Test Event',
    description: null,
    image_url: null,
    starts_at: '2026-09-01T20:00:00Z',
    ends_at: '2026-09-01T23:00:00Z',
    sale_starts_at: '2026-08-01T00:00:00Z',
    sale_ends_at: '2026-08-31T23:59:59Z',
    max_tickets_per_user: 4,
    status,
    started_at: null,
    organiser_name: 'Acme',
    venue_city: 'Barcelona',
    queue_required: false,
    created_at: '2026-07-01T00:00:00Z',
    published_at: null,
    cancelled_at: null,
  }
}

describe('EventActions', () => {
  it('shows Publish button for draft events', () => {
    render(<EventActions event={makeEvent('draft')} orgId="org-1" />)
    expect(screen.getByText('organiser.events.publish')).toBeInTheDocument()
    expect(screen.queryByText('organiser.events.markStarted')).not.toBeInTheDocument()
    expect(screen.queryByText('organiser.scanner.scanTickets')).not.toBeInTheDocument()
  })

  it('shows Mark As Started button for published events', () => {
    render(<EventActions event={makeEvent('published')} orgId="org-1" />)
    expect(screen.getByText('organiser.events.markStarted')).toBeInTheDocument()
    expect(screen.queryByText('organiser.events.publish')).not.toBeInTheDocument()
    expect(screen.queryByText('organiser.scanner.scanTickets')).not.toBeInTheDocument()
  })

  it('shows Scan button for ongoing events', () => {
    render(<EventActions event={makeEvent('ongoing')} orgId="org-1" />)
    expect(screen.getByText('organiser.scanner.scanTickets')).toBeInTheDocument()
    expect(screen.queryByText('organiser.events.publish')).not.toBeInTheDocument()
    expect(screen.queryByText('organiser.events.markStarted')).not.toBeInTheDocument()
  })

  it('renders nothing for cancelled events', () => {
    const { container } = render(<EventActions event={makeEvent('cancelled')} orgId="org-1" />)
    expect(container.firstChild).toBeNull()
  })
})
