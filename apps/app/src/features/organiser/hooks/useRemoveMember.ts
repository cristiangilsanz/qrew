// provides use remove member
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi } from '../api'

// provides use remove member
export function useRemoveMember(orgId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // implements mutation fn
    mutationFn: (userId: string) => organiserApi.removeMember(orgId, userId),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org-members', orgId] })
      toast.success(t('organiser.members.removeSuccess'))
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.removeFailed'),
      )
      toast.error(message)
    },
  })
}
