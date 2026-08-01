import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

import { PageHeader } from './page-header'

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="My Events" />)
    expect(screen.getByText('My Events')).toBeInTheDocument()
  })

  it('renders back link when backTo is provided', () => {
    render(<PageHeader title="Events" backTo="/home" />)
    expect(screen.getByRole('link')).toHaveAttribute('href', '/home')
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
