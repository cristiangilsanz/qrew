import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import type { OrgEvent } from '../api'
import { useCancelEvent } from '../hooks/useCancelEvent'
import { usePublishEvent } from '../hooks/usePublishEvent'

interface Props {
  event: OrgEvent
  orgId: string
}

export function EventActions({ event, orgId }: Props) {
  const { t } = useTranslation()
  const [confirmPublish, setConfirmPublish] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)

  const publishEvent = usePublishEvent(orgId, event.id)
  const cancelEvent = useCancelEvent(orgId, event.id)

  return (
    <div className="flex gap-2">
      {event.status === 'draft' && (
        <Button
          size="sm"
          variant={confirmPublish ? 'default' : 'outline'}
          onClick={() => {
            if (confirmPublish) {
              publishEvent.mutate()
              setConfirmPublish(false)
            } else {
              setConfirmPublish(true)
            }
          }}
          isLoading={publishEvent.isPending}
        >
          {confirmPublish ? t('organiser.events.confirmPublish') : t('organiser.events.publish')}
        </Button>
      )}
      {(event.status === 'draft' || event.status === 'published') && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            if (confirmCancel) {
              cancelEvent.mutate()
              setConfirmCancel(false)
            } else {
              setConfirmCancel(true)
            }
          }}
          isLoading={cancelEvent.isPending}
        >
          {confirmCancel ? t('organiser.events.confirmCancel') : t('organiser.events.cancel')}
        </Button>
      )}
    </div>
  )
}
