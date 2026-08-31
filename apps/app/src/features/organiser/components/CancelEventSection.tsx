// renders the cancel event section component
import { Ban } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ConfirmDialog } from '@/components/ui/confirm-dialog'

import type { OrgEvent } from '../api'
import { useCancelEvent } from '../hooks/useCancelEvent'

interface Props {
  event: OrgEvent
  orgId: string
}

// renders the cancel event section component
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
    // implements timer
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

      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        tone="destructive"
        icon={Ban}
        title={t('organiser.events.cancel')}
        description={t('organiser.events.cancelDesc')}
        irreversible
        confirmLabel={t('organiser.events.confirmCancel')}
        isLoading={cancelEvent.isPending}
        countdownSeconds={5}
        onConfirm={() => cancelEvent.mutate()}
      />
    </>
  )
}
