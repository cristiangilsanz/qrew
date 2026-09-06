// tests passkey registration step
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@simplewebauthn/browser', () => ({
  startRegistration: vi.fn().mockResolvedValue({
    id: 'mock-cred-id',
    rawId: 'mock-raw-id',
    type: 'public-key',
    response: { clientDataJSON: 'mock-client-data', attestationObject: 'mock-attestation' },
  }),
}))

// renders the toaster component
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() }, Toaster: () => null }))

import { PasskeyRegistrationStep } from './PasskeyRegistrationStep'

// implements render step
function renderStep(onSuccess = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <PasskeyRegistrationStep onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

describe('PasskeyRegistrationStep', () => {
  it('renders the create passkey button', () => {
    renderStep()
    expect(screen.getByRole('button', { name: /create passkey/i })).toBeInTheDocument()
  })

  it('calls onSuccess after successful registration', async () => {
    const onSuccess = vi.fn()
    renderStep(onSuccess)

    await userEvent.click(screen.getByRole('button', { name: /create passkey/i }))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled()
    })
  })
})
