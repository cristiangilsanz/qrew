// provides use create event
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type CreateEventData, organiserApi, type OrgEvent } from '../api'

// provides use create event
export function useCreateEvent(orgId: string, onSuccess?: (event: OrgEvent) => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: CreateEventData) => organiserApi.createEvent(orgId, data),
    // handles on success
    onSuccess: (event) => {
      void queryClient.invalidateQueries({ queryKey: ['org-events', orgId] })
      toast.success(t('organiser.events.createSuccess'))
      onSuccess?.(event)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.createEventFailed'),
      )
      toast.error(message)
    },
  })
}
