// provides use create organisation
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { type Organisation, organiserApi } from '../api'

// provides use create organisation
export function useCreateOrganisation(onSuccess?: (org: Organisation) => void) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: { slug: string; name: string; description?: string }) =>
      organiserApi.createOrg(data),
    // handles on success
    onSuccess: (org) => {
      void queryClient.invalidateQueries({ queryKey: ['organisations'] })
      toast.success(t('organiser.org.createSuccess'))
      onSuccess?.(org)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('organiser.errors.createOrgFailed'))
      toast.error(message)
    },
  })
}
