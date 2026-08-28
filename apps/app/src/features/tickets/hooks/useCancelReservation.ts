// provides use cancel reservation
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { ticketsApi } from '../api'

// provides use cancel reservation
export function useCancelReservation(reservationId: string, onSuccess?: () => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    // implements mutation fn
    mutationFn: () => ticketsApi.cancelReservation(reservationId),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['reservation', reservationId] })
      toast.success(t('tickets.reservation.cancelSuccess'))
      onSuccess?.()
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('tickets.reservation.cancelFailed'),
      )
      toast.error(message)
    },
  })
}
