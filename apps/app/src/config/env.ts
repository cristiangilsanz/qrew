export const env = {
  IDENTITY_URL: import.meta.env.VITE_IDENTITY_URL as string,
  CATALOG_URL: import.meta.env.VITE_CATALOG_URL as string,
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const
