// provides use invite member
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import type { ApiErrorDetail } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { organiserApi } from '../api'

// provides use invite member
export function useInviteCollaborator(orgId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    // implements mutation fn
    mutationFn: (data: { user_id: string; role: 'member' | 'manager' }) =>
      organiserApi.addMember(orgId, data),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org-members', orgId] })
      toast.success(t('organiser.collaborators.inviteSuccess'))
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = toastErrorMessage(error, t('organiser.errors.inviteFailed'))
      toast.error(message)
    },
  })
}
