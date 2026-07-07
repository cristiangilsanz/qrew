import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi } from '../api'

export function useDeleteTicketType(eventId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ttId: string) => organiserApi.deleteTicketType(eventId, ttId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['ticket-types', eventId] })
      toast.success(t('organiser.ticketTypes.deleteSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.deleteTicketTypeFailed'),
      )
      toast.error(message)
    },
  })
}
