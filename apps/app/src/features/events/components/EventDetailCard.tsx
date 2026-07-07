import { Link } from '@tanstack/react-router'
import { Calendar, MapPin, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

import { type EventDetail } from '../api'

interface Props {
  event: EventDetail
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatPrice(priceCents: number, currency: string): string {
  if (priceCents === 0) return 'Free'
  return `${(priceCents / 100).toFixed(2)} ${currency}`
}

export function EventDetailCard({ event }: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <p className="text-muted-foreground mb-1 text-sm font-medium">{event.organisation.name}</p>
        <h1 className="text-3xl font-bold">{event.name}</h1>
        {event.description && (
          <p className="text-muted-foreground mt-3 text-base">{event.description}</p>
        )}
      </div>

      <div className="text-muted-foreground flex flex-col gap-2 text-sm">
        <span className="flex items-center gap-2">
          <Calendar className="h-4 w-4 shrink-0" />
          <span>
            {t('events.starts')}: {formatDate(event.starts_at)}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <Calendar className="h-4 w-4 shrink-0" />
          <span>
            {t('events.ends')}: {formatDate(event.ends_at)}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <MapPin className="h-4 w-4 shrink-0" />
          <span>
            {event.venue.name}, {event.venue.city}, {event.venue.country}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <Users className="h-4 w-4 shrink-0" />
          <span>{t('events.maxPerUser', { count: event.max_tickets_per_user })}</span>
        </span>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t('events.ticketTypes')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {event.ticket_types
            .slice()
            .sort((a, b) => a.position - b.position)
            .map((tt) => (
              <div key={tt.id} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{tt.name}</p>
                  {tt.description && (
                    <p className="text-muted-foreground text-xs">{tt.description}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">
                    {formatPrice(tt.price_cents, tt.currency)}
                  </p>
                  {tt.available === 0 ? (
                    <p className="text-destructive text-xs font-medium">{t('events.soldOut')}</p>
                  ) : (
                    <p className="text-muted-foreground text-xs">
                      {t('events.available', { count: tt.available })}
                    </p>
                  )}
                </div>
              </div>
            ))}
        </CardContent>
      </Card>

      <div className="pt-2">
        {event.queue_required ? (
          <Link
            to="/events/$eventId/queue"
            params={{ eventId: event.id }}
            className="bg-primary text-primary-foreground hover:bg-primary/90 flex h-10 w-full items-center justify-center rounded-md px-4 text-sm font-medium"
          >
            {t('tickets.queue.joinButton')}
          </Link>
        ) : (
          <Link
            to="/events/$eventId/checkout"
            params={{ eventId: event.id }}
            className="bg-primary text-primary-foreground hover:bg-primary/90 flex h-10 w-full items-center justify-center rounded-md px-4 text-sm font-medium"
          >
            {t('tickets.checkout.buyButton')}
          </Link>
        )}
      </div>
    </div>
  )
}
