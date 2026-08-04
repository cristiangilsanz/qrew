import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { NotFound } from './not-found'

describe('NotFound', () => {
  it('renders the message', () => {
    render(<NotFound message="Event not found." />)
    expect(screen.getByText('Event not found.')).toBeInTheDocument()
  })

  it('renders action when provided', () => {
    render(<NotFound message="Not found." action={<button>Go back</button>} />)
    expect(screen.getByRole('button', { name: 'Go back' })).toBeInTheDocument()
  })
})
