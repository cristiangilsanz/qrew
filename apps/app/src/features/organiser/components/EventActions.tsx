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
        <>
          {confirmPublish ? (
            <>
              <Button
                size="sm"
                onClick={() => {
                  publishEvent.mutate()
                  setConfirmPublish(false)
                }}
                isLoading={publishEvent.isPending}
              >
                {t('organiser.events.confirmPublish')}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setConfirmPublish(false)}>
                {t('common.cancel')}
              </Button>
            </>
          ) : (
            <Button size="sm" variant="outline" onClick={() => setConfirmPublish(true)}>
              {t('organiser.events.publish')}
            </Button>
          )}
        </>
      )}
      {(event.status === 'draft' || event.status === 'published') && (
        <>
          {confirmCancel ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  cancelEvent.mutate()
                  setConfirmCancel(false)
                }}
                isLoading={cancelEvent.isPending}
              >
                {t('organiser.events.confirmCancel')}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setConfirmCancel(false)}>
                {t('common.cancel')}
              </Button>
            </>
          ) : (
            <Button size="sm" variant="outline" onClick={() => setConfirmCancel(true)}>
              {t('organiser.events.cancel')}
            </Button>
          )}
        </>
      )}
    </div>
  )
}
