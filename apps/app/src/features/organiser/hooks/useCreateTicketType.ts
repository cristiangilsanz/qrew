import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type CreateTicketTypeData, organiserApi } from '../api'

export function useCreateTicketType(eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateTicketTypeData) => organiserApi.createTicketType(eventId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ticket-types', eventId] })
      toast.success(t('organiser.ticketTypes.createSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.createTicketTypeFailed'),
      )
      toast.error(message)
    },
  })
}
