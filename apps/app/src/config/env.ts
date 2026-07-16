export const env = {
  IDENTITY_URL: import.meta.env.VITE_IDENTITY_URL as string,
  CATALOG_URL: import.meta.env.VITE_CATALOG_URL as string,
  SALES_URL: (import.meta.env.VITE_SALES_URL as string | undefined) ?? 'http://localhost:8003',
  PAYMENTS_URL:
    (import.meta.env.VITE_PAYMENTS_URL as string | undefined) ?? 'http://localhost:8004',
  STRIPE_PUBLISHABLE_KEY: (import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined) ?? '',
  TICKETING_URL:
    (import.meta.env.VITE_TICKETING_URL as string | undefined) ?? 'http://localhost:8005',
  GATEWAY_URL: (import.meta.env.VITE_GATEWAY_URL as string | undefined) ?? 'ws://localhost:8008',
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const
