// provides use update ticket type
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi, type UpdateTicketTypeData } from '../api'

// provides use update ticket type
export function useUpdateTicketType(eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // implements mutation fn
    mutationFn: ({ ttId, data }: { ttId: string; data: UpdateTicketTypeData }) =>
      organiserApi.updateTicketType(eventId, ttId, data),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ticket-types', eventId] })
      toast.success(t('organiser.ticketTypes.updateSuccess'))
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.updateTicketTypeFailed'),
      )
      toast.error(message)
    },
  })
}
