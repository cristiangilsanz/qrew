import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { ticketsApi } from '../api'

export function useCancelReservation(reservationId: string, onSuccess?: () => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => ticketsApi.cancelReservation(reservationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['reservation', reservationId] })
      toast.success(t('tickets.reservation.cancelSuccess'))
      onSuccess?.()
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('tickets.reservation.cancelFailed'),
      )
      toast.error(message)
    },
  })
}
