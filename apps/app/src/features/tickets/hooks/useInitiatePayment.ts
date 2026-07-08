import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type Payment, ticketsApi } from '../api'

export function useInitiatePayment(onSuccess?: (payment: Payment) => void) {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: (reservationId: string) => ticketsApi.initiatePayment(reservationId),
    onSuccess: (payment) => onSuccess?.(payment),
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('tickets.payment.initFailed'),
      )
      toast.error(message)
    },
  })
}
