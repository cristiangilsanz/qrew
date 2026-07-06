import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { passkeysApi } from '../api'

export function useDeletePasskey() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => passkeysApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['passkeys'] })
      toast.success(t('passkeys.deleteSuccess'))
    },
    onError: (error: AxiosError) => {
      const status = error.response?.status
      toast.error(
        status === 409 ? t('passkeys.errors.lastPasskey') : t('passkeys.errors.deleteFailed'),
      )
    },
  })
}
