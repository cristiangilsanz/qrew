// implements events
import { createFileRoute, Link } from '@tanstack/react-router'
import { Calendar, MapPin, Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { FloatingActions } from '@/components/ui/floating-actions'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { PageError } from '@/components/ui/page-error'
import { SEARCH_ICON_CLASS, SEARCH_INPUT_CLASS } from '@/components/ui/search-field'
import { EventCardSkeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'
import { formatDate } from '@/lib/formatDate'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/management/$orgId/events/')({
  component: OrgEventsPage,
})

// renders the org events page component
function OrgEventsPage() {
  const { t, i18n } = useTranslation()
  const { orgId } = Route.useParams()
  const [query, setQuery] = useState('')

  const { data, isLoading, isError, refetch } = useOrgEvents(orgId)
  const allEvents = data?.items ?? []
  const events = query.trim()
    ? allEvents.filter((e) => e.name.toLowerCase().includes(query.toLowerCase()))
    : allEvents

  if (isError) return <PageError onRetry={() => void refetch()} />

  return (
    <div className="mx-auto max-w-2xl p-6 pb-28">
      <BackButton to="/management/$orgId" params={{ orgId }} />
      <div className="mt-4 mb-6 space-y-4">
        <h1 className="text-2xl font-semibold">{t('organiser.events.title')}</h1>

        <div className="relative">
          <Search className={SEARCH_ICON_CLASS} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('organiser.events.searchPlaceholder')}
            className={SEARCH_INPUT_CLASS}
          />
        </div>
      </div>

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <EventCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && !isError && events.length === 0 && (
        <p className="text-muted-foreground py-8 text-center text-sm">
          {t('organiser.events.empty')}
        </p>
      )}

      <div className="space-y-4">
        {events.map((event) => {
          const imageUrl = getEventImageUrl(event.image_url)
          return (
            <Link
              key={event.id}
              to="/management/$orgId/events/$eventId"
              params={{ orgId, eventId: event.id }}
              className="block"
            >
              <article className="bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors">
                <div className="relative h-44 w-full overflow-hidden bg-[#111]">
                  <ImageWithSkeleton
                    src={imageUrl}
                    alt={event.name}
                    className={cn(
                      'h-full w-full',
                      event.image_url ? 'object-cover' : 'object-contain p-4',
                    )}
                  />
                  {event.image_url && (
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                  )}
                </div>

                <div className="space-y-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="text-base leading-snug font-semibold">{event.name}</h2>
                    <StatusChip label={event.status} />
                  </div>
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
                        {formatDate(event.starts_at, i18n.language, {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </span>
                    )}
                  </div>
                </div>
              </article>
            </Link>
          )
        })}
      </div>

      <FloatingActions>
        <Link
          to="/management/$orgId/events/new"
          params={{ orgId }}
          className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        >
          <Plus className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">{t('organiser.events.create')}</span>
        </Link>
      </FloatingActions>
    </div>
  )
}
