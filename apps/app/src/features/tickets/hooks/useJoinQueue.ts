// provides use join queue
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { ticketsApi } from '../api'

// provides use join queue
export function useJoinQueue(eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    // implements mutation fn
    mutationFn: () => ticketsApi.joinQueue(eventId),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['queue-position', eventId] })
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('tickets.queue.joinFailed'))
      toast.error(message)
    },
  })
}
