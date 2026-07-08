export const env = {
  IDENTITY_URL: import.meta.env.VITE_IDENTITY_URL as string,
  CATALOG_URL: import.meta.env.VITE_CATALOG_URL as string,
  SALES_URL: (import.meta.env.VITE_SALES_URL as string | undefined) ?? 'http://localhost:8003',
  PAYMENTS_URL:
    (import.meta.env.VITE_PAYMENTS_URL as string | undefined) ?? 'http://localhost:8004',
  STRIPE_PUBLISHABLE_KEY: (import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined) ?? '',
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const
