import { Link, createFileRoute } from '@tanstack/react-router'
import { Calendar, MapPin, Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { BackButton } from '@/components/ui/back-button'
import { StatusChip } from '@/components/ui/status-chip'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/organiser/$orgId/events/')({
  component: OrgEventsPage,
})


function OrgEventsPage() {
  const { t, i18n } = useTranslation()
  const { orgId } = Route.useParams()
  const [query, setQuery] = useState('')

  const { data, isLoading } = useOrgEvents(orgId)
  const allEvents = data?.items ?? []
  const events = query.trim()
    ? allEvents.filter((e) => e.name.toLowerCase().includes(query.toLowerCase()))
    : allEvents

  return (
    <div className="mx-auto max-w-2xl p-6 pb-28">
      <div className="mb-6 space-y-4">
        <BackButton to="/organiser/$orgId" params={{ orgId }} />
        <h1 className="text-2xl font-semibold">{t('organiser.events.title')}</h1>

        {/* Search bar */}
        <div className="relative">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('organiser.events.searchPlaceholder')}
            className="border-white/15 bg-white/5 placeholder:text-muted-foreground focus:border-primary/60 w-full rounded-2xl border py-3 pr-4 pl-9 text-sm outline-none transition-colors"
          />
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <div className="border-primary h-6 w-6 animate-spin rounded-full border-2 border-t-transparent" />
        </div>
      )}

      {!isLoading && events.length === 0 && (
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
              to="/organiser/$orgId/events/$eventId"
              params={{ orgId, eventId: event.id }}
              className="block"
            >
              <article className="bg-card border-border hover:border-primary overflow-hidden rounded-xl border transition-colors">
                {/* Image */}
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

                {/* Text */}
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
                        {new Date(event.starts_at).toLocaleDateString(i18n.language, {
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

      {/* FAB */}
      <Link
        to="/organiser/$orgId/events/new"
        params={{ orgId }}
        className="bg-primary hover:bg-primary/90 fixed bottom-24 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        style={{ right: 'max(calc((100vw - 430px) / 2 + 1.5rem), 1.5rem)' }}
      >
        <Plus className="h-5 w-5 shrink-0" />
        <span className="text-sm font-semibold">{t('organiser.events.create')}</span>
      </Link>
    </div>
  )
}
