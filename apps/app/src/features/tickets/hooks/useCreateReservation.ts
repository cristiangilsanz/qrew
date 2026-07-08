import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type Reservation, ticketsApi } from '../api'

interface CreateReservationData {
  ticket_type_id: string
  quantity: number
  reservation_window_token?: string
}

export function useCreateReservation(
  eventId: string,
  onSuccess?: (reservation: Reservation) => void,
) {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: (data: CreateReservationData) => ticketsApi.createReservation(eventId, data),
    onSuccess: (reservation) => onSuccess?.(reservation),
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('tickets.reservation.createFailed'),
      )
      toast.error(message)
    },
  })
}
