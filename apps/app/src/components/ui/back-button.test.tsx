// tests back button
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const back = vi.fn()
const navigate = vi.fn()
let canGoBack = false

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    // provides use router
    useRouter: () => ({ history: { back } }),
    // provides use can go back
    useCanGoBack: () => canGoBack,
    // provides use navigate
    useNavigate: () => navigate,
  }
})

import { BackButton } from './back-button'

describe('BackButton', () => {
  beforeEach(() => {
    back.mockClear()
    navigate.mockClear()
    canGoBack = false
  })

  it('returns to the previous step when there is history', async () => {
    canGoBack = true
    render(<BackButton to="/home" />)
    await userEvent.click(screen.getByRole('button'))
    expect(back).toHaveBeenCalledOnce()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('falls back to the given destination without history', async () => {
    render(<BackButton to="/home" />)
    await userEvent.click(screen.getByRole('button'))
    expect(back).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith({ to: '/home', params: undefined })
  })

  it('calls onClick instead of navigating when given one', async () => {
    canGoBack = true
    const onClick = vi.fn()
    render(<BackButton onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
    expect(back).not.toHaveBeenCalled()
  })
})
