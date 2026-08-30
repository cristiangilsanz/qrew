// tests page header
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

const navigate = vi.fn()

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    // renders the link component
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
    // provides use router
    useRouter: () => ({ history: { back: vi.fn() } }),
    // provides use can go back
    useCanGoBack: () => false,
    // provides use navigate
    useNavigate: () => navigate,
  }
})

import { PageHeader } from './page-header'

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="My Events" />)
    expect(screen.getByText('My Events')).toBeInTheDocument()
  })

  it('renders a back control when backTo is provided', () => {
    render(<PageHeader title="Events" backTo="/home" />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('renders children', () => {
    render(
      <PageHeader title="Events">
        <span>Filter</span>
      </PageHeader>,
    )
    expect(screen.getByText('Filter')).toBeInTheDocument()
  })
})
