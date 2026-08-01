import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EmptyState } from './empty-state'

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No results" />)
    expect(screen.getByText('No results')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<EmptyState title="Empty" description="Try searching again" />)
    expect(screen.getByText('Try searching again')).toBeInTheDocument()
  })

  it('renders image when provided', () => {
    render(<EmptyState title="Empty" image="/img.webp" imageAlt="empty" />)
    expect(screen.getByRole('img', { name: 'empty' })).toBeInTheDocument()
  })

  it('renders action when provided', () => {
    render(<EmptyState title="Empty" action={<button>Go back</button>} />)
    expect(screen.getByRole('button', { name: 'Go back' })).toBeInTheDocument()
  })
})
