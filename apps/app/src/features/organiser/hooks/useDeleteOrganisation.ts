import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi } from '../api'

export function useDeleteOrganisation() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (orgId: string) => organiserApi.deleteOrganisation(orgId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['organisations'] })
      void navigate({ to: '/organiser' })
      toast.success(t('organiser.org.deleteSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.deleteFailed'),
      )
      toast.error(message)
    },
  })
}
