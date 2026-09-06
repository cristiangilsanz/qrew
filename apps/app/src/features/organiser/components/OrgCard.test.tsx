// tests org card
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { OrgCard } from './OrgCard'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    // renders the link component
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

const mockOrg = { id: 'org-1', slug: 'acme', name: 'Acme Events' }

describe('OrgCard', () => {
  it('renders organisation name', () => {
    render(<OrgCard org={mockOrg} />)
    expect(screen.getByText('Acme Events')).toBeInTheDocument()
  })

  it('renders organisation slug', () => {
    render(<OrgCard org={mockOrg} />)
    expect(screen.getByText('@acme')).toBeInTheDocument()
  })

  it('links to management route', () => {
    render(<OrgCard org={mockOrg} />)
    expect(screen.getByRole('link')).toHaveAttribute('href', '/management/$orgId')
  })
})
