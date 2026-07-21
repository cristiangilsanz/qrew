import { Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ticketsApi } from '../api'
import { useJoinQueue } from '../hooks/useJoinQueue'
import { useQueuePosition } from '../hooks/useQueuePosition'

const POLL_MS = 2_000

interface Props {
  eventId: string
  onAdmitted?: (reservationWindowToken: string | null) => void
}

function PollBar() {
  const [progress, setProgress] = useState(100)

  useEffect(() => {
    setProgress(100)
    const start = performance.now()
    let raf: number
    const tick = (now: number) => {
      const elapsed = now - start
      const remaining = Math.max(0, 100 - (elapsed / POLL_MS) * 100)
      setProgress(remaining)
      if (remaining > 0) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div className="h-0.5 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className="bg-primary h-full rounded-full transition-none"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}

export function QueuePanel({ eventId, onAdmitted }: Props) {
  const { t } = useTranslation()
  const joinQueue = useJoinQueue(eventId)
  const { data: positionData, dataUpdatedAt } = useQueuePosition(
    eventId,
    joinQueue.isSuccess || joinQueue.isIdle === false,
  )

  const wasInQueueRef = useRef(false)
  const admittedRef = useRef(false)

  useEffect(() => {
    if (!joinQueue.isSuccess && !joinQueue.isPending) {
      joinQueue.mutate()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const position = joinQueue.isSuccess
    ? (positionData !== undefined ? positionData.position : joinQueue.data.position)
    : null
  const redeemToken = positionData?.redeem_token ?? null

  useEffect(() => {
    if (position !== null && position !== undefined) {
      wasInQueueRef.current = true
    }
    if (wasInQueueRef.current && position === null && joinQueue.isSuccess && !admittedRef.current) {
      admittedRef.current = true
      if (redeemToken) {
        ticketsApi.redeemQueue(eventId, redeemToken)
          .then((res) => onAdmitted?.(res.reservation_window_token))
          .catch(() => onAdmitted?.(null))
      } else {
        onAdmitted?.(null)
      }
    }
  }, [position, redeemToken, joinQueue.isSuccess, onAdmitted, eventId])

  if (!joinQueue.isSuccess) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="text-primary h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (position === null || position === 0) {
    return (
      <div className="space-y-3 text-center">
        <Loader2 className="text-primary mx-auto h-6 w-6 animate-spin" />
        <p className="text-muted-foreground text-sm">{t('tickets.queue.ready')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-5 text-center">
      <p className="text-muted-foreground text-sm">{t('tickets.queue.waiting')}</p>
      <span className="text-5xl font-bold tabular-nums">{position}</span>
      <div className="pt-3">
        <PollBar key={dataUpdatedAt} />
      </div>
      <p className="text-muted-foreground text-xs">{t('tickets.queue.doNotClose')}</p>
    </div>
  )
}
