import eventPlaceholder from '@/assets/images/no-event-cover.png'
import { env } from '@/config/env'

export function getEventImageUrl(key: string | null | undefined): string {
  if (!key) return eventPlaceholder
  return `${env.API_URL}/api/identity/v1/uploads/public/${key}`
}
