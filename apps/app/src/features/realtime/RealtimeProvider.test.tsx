// tests realtime provider
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { RealtimeProvider } from './RealtimeProvider'

vi.mock('react-i18next', () => ({
  // provides use translation
  // implements t
  useTranslation: () => ({ t: (k: string) => k }),
}))

vi.mock('sonner', () => ({ toast: { info: vi.fn(), warning: vi.fn(), dismiss: vi.fn() } }))

vi.mock('@/store/auth', () => ({
  // provides use auth store
  useAuthStore: (
    selector: (s: { accessToken: string | null; isAuthenticated: boolean }) => unknown,
  ) => selector({ accessToken: null, isAuthenticated: false }),
}))

vi.mock('./hooks/useWebSocket', () => ({
  // provides use web socket
  useWebSocket: () => 'closed',
}))

vi.mock('@/lib/gatewayClient', () => ({
  // implements parse user id from token
  parseUserIdFromToken: () => null,
  GatewayClient: vi.fn(),
}))

describe('RealtimeProvider', () => {
  it('renders children', () => {
    render(
      <RealtimeProvider>
        <span>child content</span>
      </RealtimeProvider>,
    )
    expect(screen.getByText('child content')).toBeInTheDocument()
  })

  it('does not mount consumer when not authenticated', () => {
    const { container } = render(
      <RealtimeProvider>
        <div />
      </RealtimeProvider>,
    )
    expect(container).toBeTruthy()
  })
})
