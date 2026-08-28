// tests bottom dock
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { BottomDock } from './BottomDock'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    // renders the link component
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
    // provides use router state
    useRouterState: ({ select }: { select: (s: { location: { pathname: string } }) => string }) =>
      select({ location: { pathname: '/home' } }),
  }
})

vi.mock('react-i18next', () => ({
  // provides use translation
  // implements t
  useTranslation: () => ({ t: (k: string) => k }),
}))

vi.mock('@/features/profile/hooks/useProfile', () => ({
  useProfile: vi.fn().mockReturnValue({ data: { is_admin: false }, isLoading: false }),
}))

vi.mock('@/features/organiser/hooks/useMyOrganisations', () => ({
  useMyOrganisations: vi.fn().mockReturnValue({ data: { items: [] }, isLoading: false }),
}))

vi.mock('@/features/tickets/hooks/useReservedTicketsCount', () => ({
  useReservedTicketsCount: vi.fn().mockReturnValue(0),
}))

vi.mock('@/features/market/hooks/useMarketAssignment', () => ({
  usePendingMarketAssignment: vi.fn().mockReturnValue({ data: null }),
}))

import { useProfile } from '@/features/profile/hooks/useProfile'

describe('BottomDock', () => {
  it('renders all base nav tabs', () => {
    render(<BottomDock />)
    expect(screen.getByText('nav.home')).toBeInTheDocument()
    expect(screen.getByText('nav.discover')).toBeInTheDocument()
    expect(screen.getByText('nav.tickets')).toBeInTheDocument()
    expect(screen.getByText('nav.market')).toBeInTheDocument()
    expect(screen.getByText('nav.profile')).toBeInTheDocument()
  })

  it('hides organiser tab for regular users with no orgs', () => {
    render(<BottomDock />)
    expect(screen.queryByText('nav.organiser')).not.toBeInTheDocument()
  })

  it('shows organiser tab for admins', () => {
    vi.mocked(useProfile).mockReturnValueOnce({
      data: { is_admin: true },
      isLoading: false,
    } as ReturnType<typeof useProfile>)
    render(<BottomDock />)
    expect(screen.getByText('nav.organiser')).toBeInTheDocument()
  })
})
