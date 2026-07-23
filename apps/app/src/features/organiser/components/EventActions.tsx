import { CheckCircle, ScanLine } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import type { OrgEvent } from '../api'
import { usePublishEvent } from '../hooks/usePublishEvent'

interface Props {
  event: OrgEvent
  orgId: string
}

export function EventActions({ event, orgId }: Props) {
  const { t } = useTranslation()

  const publishEvent = usePublishEvent(orgId, event.id)

  const showPublish = event.status === 'draft'
  const showScan = event.status === 'published'

  if (!showPublish && !showScan) return null

  return (
    <div className="fixed inset-x-0 bottom-24 z-40">
      <div className="mx-auto flex max-w-[430px] items-center justify-end gap-3 px-4">
        {showPublish && (
          <button
            onClick={() => publishEvent.mutate()}
            disabled={publishEvent.isPending}
            className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors disabled:opacity-60"
          >
            {publishEvent.isPending ? (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <CheckCircle className="h-5 w-5 shrink-0" />
            )}
            <span className="text-sm font-semibold">{t('organiser.events.publish')}</span>
          </button>
        )}
        {showScan && (
          <Link
            to="/organiser/$orgId/events/$eventId/scan"
            params={{ orgId, eventId: event.id }}
            className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
          >
            <ScanLine className="h-5 w-5 shrink-0" />
            <span className="text-sm font-semibold">{t('organiser.scanner.scanTickets')}</span>
          </Link>
        )}
      </div>
    </div>
  )
}
