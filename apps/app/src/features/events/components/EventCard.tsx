import { Calendar, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

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
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function EventCard({ event, onClick }: Props) {
  const { t } = useTranslation()
  const imageUrl = getEventImageUrl(event.image_url)

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <article
      onClick={onClick}
      className={cn(
        'bg-card border-border overflow-hidden rounded-xl border transition-colors',
        onClick && 'hover:border-primary cursor-pointer',
      )}
    >
      <div className="relative h-44 w-full overflow-hidden bg-[#111]">
        <ImageWithSkeleton
          src={imageUrl}
          alt={event.name}
          className={cn('h-full w-full', event.image_url ? 'object-cover' : 'object-contain p-4')}
        />
        {event.image_url && (
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        )}
      </div>

      <div className="space-y-2 p-4">
        <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
          {event.organiser_name ?? t('events.unknownOrganiser')}
        </p>
        <h2 className="text-base leading-snug font-semibold">{event.name}</h2>

        {event.description && (
          <p className="text-muted-foreground line-clamp-2 text-sm leading-relaxed">
            {event.description}
          </p>
        )}

        <div className="text-muted-foreground flex flex-wrap gap-3 text-xs">
          {event.venue_city && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              {event.venue_city}
            </span>
          )}
          {event.starts_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 shrink-0" />
              {formatEventDate(event.starts_at)}
            </span>
          )}
        </div>
      </div>
    </article>
  )
}
