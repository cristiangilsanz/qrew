// provides use delete organisation
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

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
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.deleteFailed'),
      )
      toast.error(message)
    },
  })
}
