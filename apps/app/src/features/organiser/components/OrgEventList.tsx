// renders the org event list component
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { ListError } from '@/components/ui/list-error'
import { OrgCardSkeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { formatDate } from '@/lib/formatDate'

import { useOrgEvents } from '../hooks/useOrgEvents'

interface Props {
  orgId: string
}

// renders the org event list component
export function OrgEventList({ orgId }: Props) {
  const { t, i18n } = useTranslation()
  const { data, isLoading, isError, refetch } = useOrgEvents(orgId)
  const events = data?.items ?? []

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <OrgCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (isError) {
    return <ListError onRetry={() => void refetch()} />
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Link
          to="/management/$orgId/events/new"
          params={{ orgId }}
          className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-8 items-center rounded-md px-3 text-sm font-medium"
        >
          {t('organiser.events.create')}
        </Link>
      </div>
      {events.length === 0 && (
        <p className="text-muted-foreground py-4 text-center text-sm">
          {t('organiser.events.empty')}
        </p>
      )}
      <div className="space-y-2">
        {events.map((event) => (
          <Link
            key={event.id}
            to="/management/$orgId/events/$eventId"
            params={{ orgId, eventId: event.id }}
            className="hover:bg-muted/50 flex items-center justify-between rounded-md border p-3 transition-colors"
          >
            <div>
              <p className="font-medium">{event.name}</p>
              <p className="text-muted-foreground text-xs">
                {formatDate(event.starts_at, i18n.language)} · {event.venue_city}
              </p>
            </div>
            <StatusChip label={event.status} />
          </Link>
        ))}
      </div>
    </div>
  )
}
