// tests event actions
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { OrgEvent } from '../api'
import { EventActions } from './EventActions'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    // renders the link component
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('react-i18next', () => ({
  // provides use translation
  // implements t
  useTranslation: () => ({ t: (k: string) => k }),
}))

vi.mock('../hooks/usePublishEvent', () => ({
  // provides use publish event
  usePublishEvent: () => ({ mutate: vi.fn(), isPending: false }),
}))

// implements make event
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
    expect(screen.queryByText('organiser.scanner.scanTickets')).not.toBeInTheDocument()
  })

  it('renders nothing for published events, which start on their own clock', () => {
    const { container } = render(<EventActions event={makeEvent('published')} orgId="org-1" />)
    expect(container.firstChild).toBeNull()
  })

  it('shows Scan button for ongoing events', () => {
    render(<EventActions event={makeEvent('ongoing')} orgId="org-1" />)
    expect(screen.getByText('organiser.scanner.scanTickets')).toBeInTheDocument()
    expect(screen.queryByText('organiser.events.publish')).not.toBeInTheDocument()
  })

  it('renders nothing for cancelled events', () => {
    const { container } = render(<EventActions event={makeEvent('cancelled')} orgId="org-1" />)
    expect(container.firstChild).toBeNull()
  })
})
