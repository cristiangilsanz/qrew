// tests how request failures are turned into what the user sees
import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'

import { fieldErrorMessage, isNotFound, toastErrorMessage } from './errors'

// builds an axios error carrying the status and body a service would return
function apiError(status: number, data: unknown): AxiosError {
  const error = new AxiosError('failed')
  error.response = {
    status,
    statusText: '',
    data,
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() },
  }
  return error
}

describe('isNotFound', () => {
  // verifies that only a missing resource counts as not found
  it('is true only for a 404 response', () => {
    expect(isNotFound(apiError(404, {}))).toBe(true)
    expect(isNotFound(apiError(500, {}))).toBe(false)
    expect(isNotFound(new Error('offline'))).toBe(false)
  })
})

describe('toastErrorMessage', () => {
  // verifies that a message the caller can act on is shown as the service wrote it
  it('keeps the service wording on a client error', () => {
    const error = apiError(409, { detail: { message: 'Slug already taken.', field: 'slug' } })
    expect(toastErrorMessage(error, 'fallback')).toBe('Slug already taken.')
  })

  // verifies that a validation list is reduced to its first entry
  it('reads the first entry of a validation list', () => {
    const error = apiError(422, { detail: [{ msg: 'Email rejected.' }] })
    expect(toastErrorMessage(error, 'fallback')).toBe('Email rejected.')
  })

  // verifies that a server fault never leaks its own wording
  it('falls back on a server error', () => {
    expect(toastErrorMessage(apiError(500, { detail: 'boom' }), 'fallback')).toBe('fallback')
  })

  // verifies that a failure with no response falls back
  it('falls back when the request never reached a service', () => {
    expect(toastErrorMessage(new AxiosError('offline'), 'fallback')).toBe('fallback')
    expect(toastErrorMessage(new Error('offline'), 'fallback')).toBe('fallback')
  })
})

describe('fieldErrorMessage', () => {
  // verifies that only a message naming a field is offered to the form
  it('returns the message when it names a field', () => {
    const error = apiError(400, { detail: { message: 'Quantity rejected.', field: 'quantity' } })
    expect(fieldErrorMessage(error)).toBe('Quantity rejected.')
  })

  // verifies that a message without a field is not shown as a field error
  it('returns null when no field is named', () => {
    const error = apiError(400, { detail: { message: 'Something', field: null } })
    expect(fieldErrorMessage(error)).toBeNull()
    expect(fieldErrorMessage(apiError(500, {}))).toBeNull()
  })
})
