// provides use create venue
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { type CreateVenueData, organiserApi, type Venue } from '../api'

// provides use create venue
export function useCreateVenue(onSuccess?: (venue: Venue) => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: CreateVenueData) => organiserApi.createVenue(data),
    // handles on success
    onSuccess: (venue) => {
      void queryClient.invalidateQueries({ queryKey: ['venues'] })
      toast.success(t('organiser.venues.createSuccess'))
      onSuccess?.(venue)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('organiser.errors.createVenueFailed'))
      toast.error(message)
    },
  })
}
