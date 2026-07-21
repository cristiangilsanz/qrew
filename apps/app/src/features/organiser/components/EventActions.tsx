import { AnimatePresence, motion } from 'framer-motion'
import { Ban, CheckCircle, ScanLine } from 'lucide-react'
import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import type { OrgEvent } from '../api'
import { useCancelEvent } from '../hooks/useCancelEvent'
import { usePublishEvent } from '../hooks/usePublishEvent'

interface Props {
  event: OrgEvent
  orgId: string
}

export function EventActions({ event, orgId }: Props) {
  const { t } = useTranslation()
  const [confirmCancel, setConfirmCancel] = useState(false)

  const publishEvent = usePublishEvent(orgId, event.id)
  const cancelEvent = useCancelEvent(orgId, event.id)

  const showPublish = event.status === 'draft'
  const showCancel = event.status === 'draft' || event.status === 'published'
  const showScan = event.status === 'published'

  if (!showPublish && !showCancel && !showScan) return null

  return (
    <>
      <div className="flex items-center justify-between gap-3">
        {/* Cancel — left */}
        {showCancel ? (
          <button
            onClick={() => setConfirmCancel(true)}
            className="flex h-14 items-center gap-2 rounded-full bg-red-500/90 px-5 text-white shadow-lg transition-colors hover:bg-red-500"
          >
            <Ban className="h-5 w-5 shrink-0" />
            <span className="text-sm font-semibold">{t('organiser.events.cancel')}</span>
          </button>
        ) : (
          <div />
        )}

        {/* Publish / Scan — right */}
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

      {/* Cancel confirmation modal */}
      <AnimatePresence>
        {confirmCancel && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setConfirmCancel(false)}
          >
            <motion.div
              initial={{ y: 32, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 32, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <Ban className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-red-400">
                    {t('organiser.events.cancel')}
                  </h3>
                  <p className="text-muted-foreground text-xs">{event.name}</p>
                </div>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">
                {t('organiser.events.cancelDesc')}
              </p>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                  onClick={() => setConfirmCancel(false)}
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => {
                    cancelEvent.mutate()
                    setConfirmCancel(false)
                  }}
                  disabled={cancelEvent.isPending}
                  className="flex h-10 items-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {cancelEvent.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <Ban className="h-3.5 w-3.5" />
                  )}
                  {t('organiser.events.confirmCancel')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
