// tests confirm dialog
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { CSSProperties, MouseEvent, ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { ConfirmDialog } from './confirm-dialog'

vi.mock('framer-motion', () => ({
  // renders the animate presence component
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    // implements div
    div: ({
      children,
      onClick,
      className,
      style,
    }: {
      children: ReactNode
      onClick?: (e: MouseEvent) => void
      className?: string
      style?: CSSProperties
    }) => (
      // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
      <div onClick={onClick} className={className} style={style}>
        {children}
      </div>
    ),
  },
}))

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  title: 'Delete item',
  confirmLabel: 'Delete',
  onConfirm: vi.fn(),
}

describe('ConfirmDialog', () => {
  it('renders title and confirm button when open', () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText('Delete item')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<ConfirmDialog {...defaultProps} description="The item will be removed." />)
    expect(screen.getByText('The item will be removed.')).toBeInTheDocument()
  })

  it('warns that the action cannot be undone when it is irreversible', () => {
    const { container } = render(<ConfirmDialog {...defaultProps} irreversible />)
    expect(container.textContent).toContain('This cannot be undone.')
  })

  it('leaves the warning out when the action can be undone', () => {
    const { container } = render(<ConfirmDialog {...defaultProps} />)
    expect(container.textContent).not.toContain('This cannot be undone.')
  })

  it('holds the confirm button until the countdown runs out', () => {
    const { container } = render(<ConfirmDialog {...defaultProps} countdownSeconds={5} />)
    expect(container.textContent).toContain('Wait 5s')
    expect(screen.getByText('Wait 5s').closest('button')).toBeDisabled()
  })

  it('renders whatever it is given to show alongside the question', () => {
    render(
      <ConfirmDialog {...defaultProps}>
        <p>Type your password</p>
      </ConfirmDialog>,
    )
    expect(screen.getByText('Type your password')).toBeInTheDocument()
  })

  it('renders nothing when closed', () => {
    const { container } = render(<ConfirmDialog {...defaultProps} open={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('calls onConfirm when confirm button clicked', async () => {
    const onConfirm = vi.fn()
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />)
    await userEvent.click(screen.getByText('Delete'))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('calls onOpenChange(false) when cancel button clicked', async () => {
    const onOpenChange = vi.fn()
    render(<ConfirmDialog {...defaultProps} onOpenChange={onOpenChange} />)
    await userEvent.click(screen.getByText('Go Back'))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('disables buttons while loading', () => {
    render(<ConfirmDialog {...defaultProps} isLoading />)
    const buttons = screen.getAllByRole('button')
    buttons.forEach((btn) => expect(btn).toBeDisabled())
  })
})
