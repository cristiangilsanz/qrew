// tests org event list
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { OrgEventList } from './OrgEventList'

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
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: 'en' } }),
}))

vi.mock('@/lib/formatDate', () => ({
  // implements format date
  formatDate: () => '1 Sep 2026',
}))

vi.mock('../hooks/useOrgEvents', () => ({
  useOrgEvents: vi.fn(),
}))

import { useOrgEvents } from '../hooks/useOrgEvents'

const mockedUseOrgEvents = vi.mocked(useOrgEvents)

describe('OrgEventList', () => {
  it('shows skeleton while loading', () => {
    mockedUseOrgEvents.mockReturnValue({ data: undefined, isLoading: true } as ReturnType<
      typeof useOrgEvents
    >)
    const { container } = render(<OrgEventList orgId="org-1" />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('shows empty message when no events', () => {
    mockedUseOrgEvents.mockReturnValue({
      data: { items: [], next_cursor: null },
      isLoading: false,
    } as ReturnType<typeof useOrgEvents>)
    render(<OrgEventList orgId="org-1" />)
    expect(screen.getByText('organiser.events.empty')).toBeInTheDocument()
  })

  it('renders event names', () => {
    mockedUseOrgEvents.mockReturnValue({
      data: {
        items: [
          {
            id: 'e1',
            name: 'Event Alpha',
            status: 'published',
            starts_at: '2026-09-01T20:00:00Z',
            venue_city: 'Madrid',
          },
          {
            id: 'e2',
            name: 'Event Beta',
            status: 'draft',
            starts_at: '2026-10-01T20:00:00Z',
            venue_city: 'Berlin',
          },
        ],
        next_cursor: null,
      },
      isLoading: false,
    } as ReturnType<typeof useOrgEvents>)
    render(<OrgEventList orgId="org-1" />)
    expect(screen.getByText('Event Alpha')).toBeInTheDocument()
    expect(screen.getByText('Event Beta')).toBeInTheDocument()
  })

  it('renders create event link', () => {
    mockedUseOrgEvents.mockReturnValue({
      data: { items: [], next_cursor: null },
      isLoading: false,
    } as ReturnType<typeof useOrgEvents>)
    render(<OrgEventList orgId="org-1" />)
    expect(screen.getByText('organiser.events.create')).toBeInTheDocument()
  })
})
