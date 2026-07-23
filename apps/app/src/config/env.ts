const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

const _wsHost =
  (import.meta.env.VITE_GATEWAY_URL as string | undefined) ??
  (typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://localhost:5173')

export const env = {
  API_URL,
  STRIPE_PUBLISHABLE_KEY: (import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined) ?? '',
  GATEWAY_URL: _wsHost,
  GOOGLE_MAPS_API_KEY: (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined) ?? '',
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const
