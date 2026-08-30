// provides use initiate payment
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { type Payment, ticketsApi } from '../api'

// provides use initiate payment
export function useInitiatePayment(onSuccess?: (payment: Payment) => void) {
  const { t } = useTranslation()
  return useMutation({
    // implements mutation fn
    mutationFn: (reservationId: string) => ticketsApi.initiatePayment(reservationId),
    // handles on success
    onSuccess: (payment) => onSuccess?.(payment),
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('tickets.payment.initFailed'))
      toast.error(message)
    },
  })
}
