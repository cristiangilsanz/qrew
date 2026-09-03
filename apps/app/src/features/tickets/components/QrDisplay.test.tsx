// tests qr display
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { QrDisplay } from './QrDisplay'

vi.mock('react-i18next', () => ({
  // provides use translation
  // implements t
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('react-qr-code', () => ({
  // implements default
  default: ({ value }: { value: string }) => <div data-testid="qr-code">{value}</div>,
}))

vi.mock('@/store/auth', () => ({
  // implements get state
  useAuthStore: { getState: () => ({ accessToken: 'mock-token' }) },
}))

vi.mock('@/config/env', () => ({
  env: { API_URL: 'http://localhost:8000' },
}))

const reassert = vi.fn().mockResolvedValue('fresh-token')

vi.mock('@/features/passkeys/hooks/useReassertPasskey', () => ({
  // provides use reassert passkey
  useReassertPasskey: () => reassert,
}))

vi.mock('@capacitor/geolocation', () => ({
  Geolocation: {
    requestPermissions: vi.fn().mockResolvedValue({ location: 'granted' }),
    getCurrentPosition: vi.fn().mockResolvedValue({
      coords: { latitude: 40.4, longitude: -3.7 },
    }),
  },
}))

// implements make client
const makeClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

// implements wrapper
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={makeClient()}>{children}</QueryClientProvider>
)

describe('QrDisplay', () => {
  beforeEach(() => {
    reassert.mockClear()
    reassert.mockResolvedValue('fresh-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        // implements json
        json: () =>
          Promise.resolve({
            jwt: 'test.jwt.token',
            expires_at: new Date(Date.now() + 30000).toISOString(),
          }),
      }),
    )
  })

  it('proves presence with the passkey before it asks for a code', async () => {
    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })

    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByTestId('qr-code')).toBeInTheDocument()
    })
    expect(reassert).toHaveBeenCalled()
  })

  it('shows no code when the holder refuses to prove presence', async () => {
    reassert.mockRejectedValueOnce(new Error('cancelled'))

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })

    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.deniedReassertion')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('qr-code')).not.toBeInTheDocument()
  })

  it('asks again and retries when the presence window lapses', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        // implements json
        json: () => Promise.resolve({ detail: { field: 'reassertion' } }),
      })
      .mockResolvedValue({
        ok: true,
        // implements json
        json: () =>
          Promise.resolve({
            jwt: 'second.jwt.token',
            expires_at: new Date(Date.now() + 30000).toISOString(),
          }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByTestId('qr-code')).toHaveTextContent('second.jwt.token')
    })
    expect(reassert).toHaveBeenCalledTimes(2)
  })

  it('gives up after one retry so it cannot loop', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        // implements json
        json: () => Promise.resolve({ detail: { field: 'reassertion' } }),
      }),
    )

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.deniedReassertion')).toBeInTheDocument()
    })
    expect(reassert).toHaveBeenCalledTimes(2)
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
    const { Geolocation } = await import('@capacitor/geolocation')
    vi.mocked(Geolocation.getCurrentPosition).mockRejectedValueOnce(new Error('denied'))

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
      vi.fn().mockResolvedValue({
        ok: false,
        // implements json
        json: () =>
          Promise.resolve({
            detail: { field: 'geofence' },
          }),
      }),
    )

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.deniedGeofence')).toBeInTheDocument()
    })
  })

  it('shows retry button after denial', async () => {
    const { Geolocation } = await import('@capacitor/geolocation')
    vi.mocked(Geolocation.getCurrentPosition).mockRejectedValueOnce(new Error('denied'))

    const user = userEvent.setup()
    render(<QrDisplay ticketId="ticket-1" />, { wrapper })
    await user.click(screen.getByText('tickets.qr.showButton'))

    await waitFor(() => {
      expect(screen.getByText('tickets.qr.retry')).toBeInTheDocument()
    })
  })
})
