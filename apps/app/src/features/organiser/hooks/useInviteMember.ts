import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { type ApiErrorDetail, extractErrorMessage } from '@/features/auth/api'

import { organiserApi } from '../api'

export function useInviteMember(orgId: string) {
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: { email: string; role: 'member' | 'manager' | 'owner' }) =>
      organiserApi.inviteMember(orgId, data),
    onSuccess: () => {
      toast.success(t('organiser.members.inviteSuccess'))
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('organiser.errors.inviteFailed'),
      )
      toast.error(message)
    },
  })
}
