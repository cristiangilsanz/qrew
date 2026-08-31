// renders the event actions component
import { Link } from '@tanstack/react-router'
import { CheckCircle, Play, ScanLine } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ConfirmDialog } from '@/components/ui/confirm-dialog'

import type { OrgEvent } from '../api'
import { usePublishEvent } from '../hooks/usePublishEvent'
import { useStartEvent } from '../hooks/useStartEvent'

interface Props {
  event: OrgEvent
  orgId: string
}

// renders the event actions component
export function EventActions({ event, orgId }: Props) {
  const { t } = useTranslation()

  const publishEvent = usePublishEvent(orgId, event.id)
  const startEvent = useStartEvent(orgId, event.id)
  const [startOpen, setStartOpen] = useState(false)

  const showPublish = event.status === 'draft'
  const showMarkStarted = event.status === 'published'
  const showScan = event.status === 'ongoing'

  if (!showPublish && !showMarkStarted && !showScan) return null

  return (
    <div className="keyboard-hide fixed inset-x-0 bottom-24 z-40">
      <div className="mx-auto flex w-full max-w-[430px] items-center justify-end gap-3 px-4">
        {showPublish && (
          <button
            onClick={() => publishEvent.mutate()}
            disabled={publishEvent.isPending}
            className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors disabled:opacity-60"
          >
            <CheckCircle className="h-5 w-5 shrink-0" />
            <span className="text-sm font-semibold">{t('organiser.events.publish')}</span>
          </button>
        )}
        {showMarkStarted && (
          <button
            onClick={() => setStartOpen(true)}
            disabled={startEvent.isPending}
            className="flex h-14 items-center gap-2 rounded-full bg-green-600 px-5 text-white shadow-lg transition-colors hover:bg-green-500 disabled:opacity-60"
          >
            <Play className="h-5 w-5 shrink-0" />
            <span className="text-sm font-semibold">{t('organiser.events.markStarted')}</span>
          </button>
        )}
        {showScan && (
          <Link
            to="/management/$orgId/events/$eventId/scan"
            params={{ orgId, eventId: event.id }}
            className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
          >
            <ScanLine className="h-5 w-5 shrink-0" />
            <span className="text-sm font-semibold">{t('organiser.scanner.scanTickets')}</span>
          </Link>
        )}
      </div>

      <ConfirmDialog
        open={startOpen}
        onOpenChange={setStartOpen}
        tone="warning"
        icon={Play}
        title={t('organiser.events.markStartedTitle')}
        description={t('organiser.events.markStartedDescription')}
        note={t('organiser.events.markStartedNote')}
        confirmLabel={t('organiser.events.markStartedConfirm')}
        cancelLabel={t('common.goBack')}
        isLoading={startEvent.isPending}
        onConfirm={() =>
          startEvent.mutate(undefined, {
            // closes the dialog once the event has actually started
            onSuccess: () => setStartOpen(false),
          })
        }
      />
    </div>
  )
}
