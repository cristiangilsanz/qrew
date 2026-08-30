// provides use delete organisation
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { organiserApi } from '../api'

// provides use delete organisation
export function useDeleteOrganisation() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    // implements mutation fn
    mutationFn: (orgId: string) => organiserApi.deleteOrganisation(orgId),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['organisations'] })
      void navigate({ to: '/management' })
      toast.success(t('organiser.org.deleteSuccess'))
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('organiser.errors.deleteFailed'))
      toast.error(message)
    },
  })
}
