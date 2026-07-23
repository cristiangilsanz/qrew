import { AnimatePresence, motion } from 'framer-motion'
import { Ban } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { OrgEvent } from '../api'
import { useCancelEvent } from '../hooks/useCancelEvent'

interface Props {
  event: OrgEvent
  orgId: string
}

export function CancelEventSection({ event, orgId }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [countdown, setCountdown] = useState(5)
  const cancelEvent = useCancelEvent(orgId, event.id)

  useEffect(() => {
    if (!open) {
      setCountdown(5)
      return
    }
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [open, countdown])

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-white/5"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500/10">
          <Ban className="h-4 w-4 text-red-400" />
        </div>
        <span className="flex-1 text-sm font-semibold text-red-400">
          {t('organiser.events.cancel')}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setOpen(false)}
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
                <h3 className="text-base font-semibold text-red-400">
                  {t('organiser.events.cancel')}
                </h3>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">
                {t('organiser.events.cancelDesc')}
              </p>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                  onClick={() => setOpen(false)}
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => {
                    cancelEvent.mutate()
                    setOpen(false)
                  }}
                  disabled={countdown > 0 || cancelEvent.isPending}
                  className="flex h-10 min-w-[112px] items-center justify-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {cancelEvent.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : countdown > 0 ? (
                    t('common.waitSeconds', { seconds: countdown })
                  ) : (
                    <>
                      <Ban className="h-3.5 w-3.5" />
                      {t('organiser.events.confirmCancel')}
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
