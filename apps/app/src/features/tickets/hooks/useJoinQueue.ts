import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { ticketsApi } from '../api'

export function useJoinQueue(eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => ticketsApi.joinQueue(eventId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['queue-position', eventId] })
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('tickets.queue.joinFailed'),
      )
      toast.error(message)
    },
  })
}
