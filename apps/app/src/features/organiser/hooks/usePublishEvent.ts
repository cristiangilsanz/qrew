import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi } from '../api'

export function usePublishEvent(orgId: string, eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => organiserApi.publishEvent(eventId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org-events', orgId] })
      void queryClient.invalidateQueries({ queryKey: ['event', eventId] })
      toast.success(t('organiser.events.publishSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.publishFailed'),
      )
      toast.error(message)
    },
  })
}
