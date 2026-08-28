// tests status chip
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusChip } from './status-chip'

describe('StatusChip', () => {
  it('renders the label', () => {
    render(<StatusChip label="Published" />)
    expect(screen.getByText('Published')).toBeInTheDocument()
  })

  it('uses variant key when provided', () => {
    const { container } = render(<StatusChip label="Active" variant="ongoing" />)
    expect(container.firstChild).toHaveClass('text-green-400')
  })

  it('falls back to default style for unknown variant', () => {
    const { container } = render(<StatusChip label="Unknown" variant="unknown_status" />)
    expect(container.firstChild).toHaveClass('text-white/50')
  })
})
