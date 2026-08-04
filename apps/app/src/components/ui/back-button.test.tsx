import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    Link: ({ children, to }: { children: unknown; to: string }) => <a href={to}>{children}</a>,
  }
})

import { BackButton } from './back-button'

describe('BackButton', () => {
  it('renders a link when to is provided', () => {
    render(<BackButton to="/home" />)
    expect(screen.getByRole('link')).toHaveAttribute('href', '/home')
  })

  it('renders a button and calls onClick', async () => {
    const onClick = vi.fn()
    render(<BackButton onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})
