// provides use redeem queue
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { ticketsApi } from '../api'

// provides use redeem queue
export function useRedeemQueue(eventId: string) {
  const { t } = useTranslation()
  return useMutation({
    // implements mutation fn
    mutationFn: (redeemWindowToken: string) => ticketsApi.redeemQueue(eventId, redeemWindowToken),
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('tickets.queue.redeemFailed'),
      )
      toast.error(message)
    },
  })
}
