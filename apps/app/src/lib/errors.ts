// tells apart the failures a user can act on from the ones that only alarm them
import axios from 'axios'

// reports whether a query failed because the resource is not there
export function isNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404
}

// reads the message a request came back with when it names a field the user can fix
export function fieldErrorMessage(error: unknown): string | null {
  if (!axios.isAxiosError(error)) return null
  const status = error.response?.status
  if (status === undefined || status < 400 || status >= 500) return null
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.field ? detail.message : null
  }
  return null
}

// picks the wording a toast shows, keeping backend detail only for errors the user can act on
export function toastErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback
  const status = error.response?.status
  if (status === undefined || status < 400 || status >= 500) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail[0]?.msg ?? fallback
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message
  }
  return fallback
}
