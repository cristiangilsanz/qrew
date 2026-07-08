import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import { useJoinQueue } from '../hooks/useJoinQueue'
import { useQueuePosition } from '../hooks/useQueuePosition'

interface Props {
  eventId: string
}

export function QueuePanel({ eventId }: Props) {
  const { t } = useTranslation()
  const joinQueue = useJoinQueue(eventId)
  const { data: positionData, isLoading: positionLoading } = useQueuePosition(
    eventId,
    joinQueue.isSuccess || joinQueue.isIdle === false,
  )

  if (!joinQueue.isSuccess) {
    return (
      <div className="space-y-3 text-center">
        <p className="text-muted-foreground text-sm">{t('tickets.queue.description')}</p>
        <Button
          onClick={() => joinQueue.mutate()}
          isLoading={joinQueue.isPending}
          className="w-full"
        >
          {t('tickets.queue.joinButton')}
        </Button>
      </div>
    )
  }

  const position = positionData?.position ?? joinQueue.data.position

  if (position === null) {
    return (
      <div className="space-y-2 text-center">
        <p className="text-sm font-medium">{t('tickets.queue.notInQueue')}</p>
      </div>
    )
  }

  if (position === 0) {
    return (
      <div className="space-y-2 text-center">
        <p className="text-lg font-semibold text-green-600">{t('tickets.queue.ready')}</p>
        <p className="text-muted-foreground text-sm">{t('tickets.queue.readyDescription')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3 text-center">
      <p className="text-muted-foreground text-sm">{t('tickets.queue.waiting')}</p>
      <div className="flex items-center justify-center gap-2">
        <span className="text-4xl font-bold">{position}</span>
        {positionLoading && <Loader2 className="text-muted-foreground h-5 w-5 animate-spin" />}
      </div>
      <p className="text-muted-foreground text-xs">{t('tickets.queue.positionHint')}</p>
    </div>
  )
}
