import { Link, createFileRoute } from '@tanstack/react-router'
import { ChevronRight, FileEdit, Ticket } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { EventActions } from '@/features/organiser/components/EventActions'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/organiser/$orgId/events/$eventId/')({
  component: EventManagePage,
})

function EventManagePage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()
  const { data } = useOrgEvents(orgId)
  const event = data?.items.find((e) => e.id === eventId)

  if (!event) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <div className="flex justify-center py-8">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        </div>
      </div>
    )
  }

  const imageUrl = getEventImageUrl(event.image_url)

  return (
    <div className="pb-28">
      {/* Hero */}
      <div className="relative h-56 overflow-hidden bg-[#111]">
        <ImageWithSkeleton
          src={imageUrl}
          alt={event.name}
          className={cn(
            'absolute inset-0 h-full w-full',
            event.image_url ? 'object-cover opacity-80' : 'object-contain p-8 opacity-40',
          )}
        />
        {event.image_url && (
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-transparent" />
        )}
        {/* bottom fade */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent" />

        <BackButton
          to="/organiser/$orgId/events"
          params={{ orgId }}
          className="absolute top-4 left-4"
        />
      </div>

      {/* Content */}
      <div className="mx-auto max-w-2xl space-y-6 px-4 pt-4">
        {/* Title + status chip */}
        <div className="flex items-center gap-3">
          <h1 className="flex-1 text-2xl font-semibold">{event.name}</h1>
          {event.status && <StatusChip label={event.status} />}
        </div>

        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          {(event.status === 'draft' || event.status === 'published') && (
            <>
              <Link
                to="/organiser/$orgId/events/$eventId/edit"
                params={{ orgId, eventId }}
                className="hover:bg-white/[0.04] flex w-full items-center gap-3 px-4 py-4 transition-colors"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
                  <FileEdit className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{t('organiser.events.edit')}</p>
                  <p className="text-muted-foreground text-xs">Manage date, venue, image, description and max tickets per user</p>
                </div>
                <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
              </Link>
              <div className="border-t border-white/10" />
            </>
          )}
          <Link
            to="/organiser/$orgId/events/$eventId/tickets"
            params={{ orgId, eventId }}
            className="hover:bg-white/[0.04] flex w-full items-center gap-3 px-4 py-4 transition-colors"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
              <Ticket className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{t('organiser.ticketTypes.title')}</p>
              <p className="text-muted-foreground text-xs">Manage pricing and capacity</p>
            </div>
            <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
          </Link>
        </div>

        <EventActions event={event} orgId={orgId} />
      </div>
    </div>
  )
}
