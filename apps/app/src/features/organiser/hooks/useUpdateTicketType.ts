import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi, type UpdateTicketTypeData } from '../api'

export function useUpdateTicketType(eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ttId, data }: { ttId: string; data: UpdateTicketTypeData }) =>
      organiserApi.updateTicketType(eventId, ttId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ticket-types', eventId] })
      toast.success(t('organiser.ticketTypes.updateSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.updateTicketTypeFailed'),
      )
      toast.error(message)
    },
  })
}
