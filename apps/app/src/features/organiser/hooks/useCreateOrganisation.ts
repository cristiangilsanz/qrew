import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { type Organisation, organiserApi } from '../api'

export function useCreateOrganisation(onSuccess?: (org: Organisation) => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { slug: string; name: string; description?: string }) =>
      organiserApi.createOrg(data),
    onSuccess: (org) => {
      void queryClient.invalidateQueries({ queryKey: ['organisations'] })
      toast.success(t('organiser.org.createSuccess'))
      onSuccess?.(org)
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.createOrgFailed'),
      )
      toast.error(message)
    },
  })
}
