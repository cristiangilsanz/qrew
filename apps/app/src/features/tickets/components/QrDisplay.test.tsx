import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { QrDisplay } from './QrDisplay'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('react-qr-code', () => ({
  default: ({ value }: { value: string }) => <div data-testid="qr-code">{value}</div>,
}))

vi.mock('@/store/auth', () => ({
  useAuthStore: { getState: () => ({ accessToken: 'mock-token' }) },
}))

vi.mock('@/config/env', () => ({
  env: { API_URL: 'http://localhost:8000' },
}))

const makeClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={makeClient()}>{children}</QueryClientProvider>
)

describe('QrDisplay', () => {
  beforeEach(() => {
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn((success: PositionCallback) =>
          success({ coords: { latitude: 40.4, longitude: -3.7 } } as GeolocationPosition),
        ),
      },
    })

    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode(
                    'event: qr\ndata: {"jwt":"test.jwt.token","expires_at":"2026-01-01T00:00:20Z"}\n\n',
                  ),
                })
                .mockResolvedValueOnce({ done: true, value: undefined }),
            }),
          },
        }),
      ),
    )
  })

  it('shows show QR button initially', () => {
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    expect(screen.getByText('tickets.qr.showButton')).toBeInTheDocument()
  })

  it('shows QR code after successful stream', async () => {
    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })

    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByTestId('qr-code')).toBeInTheDocument()
    })
    expect(screen.getByTestId('qr-code')).toHaveTextContent('test.jwt.token')
  })

  it('shows geolocation denied message when geo fails', async () => {
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn((_success: unknown, error: PositionErrorCallback) =>
          error({ code: 1, message: 'denied' } as GeolocationPositionError),
        ),
      },
    })

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })

    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.deniedLocation')).toBeInTheDocument()
    })
  })

  it('shows geofence denied message when stream returns denied event', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode(
                    'event: denied\ndata: {"type":"denied","detail":{"field":"geofence"}}\n\n',
                  ),
                })
                .mockResolvedValueOnce({ done: true, value: undefined }),
            }),
          },
        }),
      ),
    )

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.deniedGeofence')).toBeInTheDocument()
    })
  })

  it('shows retry button after denial', async () => {
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn((_success: unknown, error: PositionErrorCallback) =>
          error({ code: 1, message: 'denied' } as GeolocationPositionError),
        ),
      },
    })

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.retry')).toBeInTheDocument()
    })
  })
})
