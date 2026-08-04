import eventPlaceholder from '@/assets/images/illustrations/event-cover.webp'
import { env } from '@/config/env'

export function getEventImageUrl(key: string | null | undefined): string {
  if (!key) return eventPlaceholder
  if (key.startsWith('http://') || key.startsWith('https://')) return key
  return `${env.API_URL}/api/identity/v1/uploads/public/${key}`
}
