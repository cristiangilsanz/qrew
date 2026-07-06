import { Calendar, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '@/components/ui/card'

import { type EventSummary } from '../api'

interface Props {
  event: EventSummary
  onClick?: () => void
}

function formatEventDate(isoString: string | null): string {
  if (!isoString) return ''
  return new Date(isoString).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function EventCard({ event, onClick }: Props) {
  const { t } = useTranslation()

  return (
    <Card
      className="hover:border-primary cursor-pointer transition-colors"
      onClick={onClick}
      role="article"
    >
      <CardContent className="p-4">
        <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">
          {event.organiser_name ?? t('events.unknownOrganiser')}
        </p>
        <h2 className="mb-2 text-base font-semibold">{event.name}</h2>
        <div className="text-muted-foreground flex flex-wrap gap-3 text-sm">
          {event.venue_city && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {event.venue_city}
            </span>
          )}
          {event.starts_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatEventDate(event.starts_at)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
