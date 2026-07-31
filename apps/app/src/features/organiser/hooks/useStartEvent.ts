import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi } from '../api'

export function useStartEvent(orgId: string, eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => organiserApi.startEvent(eventId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org-events', orgId] })
      void queryClient.invalidateQueries({ queryKey: ['events', eventId] })
      toast.success(t('organiser.events.startSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.startFailed'),
      )
      toast.error(message)
    },
  })
}
