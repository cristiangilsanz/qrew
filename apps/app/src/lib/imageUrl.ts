import eventPlaceholder from '@/assets/images/no-event-cover.png'

const IDENTITY_URL = import.meta.env.VITE_IDENTITY_URL ?? 'http://localhost:8001'

export function getEventImageUrl(key: string | null | undefined): string {
  if (!key) return eventPlaceholder
  return `${IDENTITY_URL}/v1/uploads/public/${key}`
}
