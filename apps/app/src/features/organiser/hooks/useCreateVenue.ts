import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type CreateVenueData, organiserApi, type Venue } from '../api'

export function useCreateVenue(onSuccess?: (venue: Venue) => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateVenueData) => organiserApi.createVenue(data),
    onSuccess: (venue) => {
      void queryClient.invalidateQueries({ queryKey: ['venues'] })
      toast.success(t('organiser.venues.createSuccess'))
      onSuccess?.(venue)
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.createVenueFailed'),
      )
      toast.error(message)
    },
  })
}
