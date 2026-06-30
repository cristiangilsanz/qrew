export const env = {
  API_URL: import.meta.env.VITE_API_URL as string,
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const
