import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { passkeysApi } from '../api'

export function useRenamePasskey() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => passkeysApi.rename(id, name),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['passkeys'] })
      toast.success(t('passkeys.renameSuccess'))
    },
    onError: () => {
      toast.error(t('passkeys.errors.renameFailed'))
    },
  })
}
