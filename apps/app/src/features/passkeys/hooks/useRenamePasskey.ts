// provides use rename passkey
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { passkeysApi } from '../api'

// provides use rename passkey
export function useRenamePasskey() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  return useMutation({
    // implements mutation fn
    mutationFn: ({ id, name }: { id: string; name: string }) => passkeysApi.rename(id, name),
    // handles on success
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['passkeys'] })
      toast.success(t('passkeys.renameSuccess'))
    },
    // handles on error
    onError: () => {
      toast.error(t('passkeys.errors.renameFailed'))
    },
  })
}
