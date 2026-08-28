// renders the passkey list component
import { useQueryClient } from '@tanstack/react-query'
import { KeyRound, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useRegisterPasskey } from '@/features/onboarding/hooks/useRegisterPasskey'
import { formatDate } from '@/lib/formatDate'

import { useDeletePasskey } from '../hooks/useDeletePasskey'
import { usePasskeys } from '../hooks/usePasskeys'
import { useRenamePasskey } from '../hooks/useRenamePasskey'

// renders the passkey list component
export function PasskeyList() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const { data, isLoading } = usePasskeys()
  const deletePasskey = useDeletePasskey()
  const renamePasskey = useRenamePasskey()
  // implements register passkey
  const registerPasskey = useRegisterPasskey(() => {
    void queryClient.invalidateQueries({ queryKey: ['passkeys'] })
    void queryClient.invalidateQueries({ queryKey: ['onboarding-status'] })
  })
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <div key={i} className="flex items-center gap-3 rounded-xl bg-white/[0.04] px-3 py-3">
            <Skeleton className="h-5 w-5 rounded" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-7 w-7 rounded" />
            <Skeleton className="h-7 w-7 rounded" />
          </div>
        ))}
      </div>
    )
  }

  const passkeys = data?.items ?? []

  return (
    <div className="space-y-3">
      {passkeys.length === 0 && (
        <p className="text-muted-foreground py-2 text-center text-sm">{t('passkeys.empty')}</p>
      )}
      <ul className="space-y-2">
        {passkeys.map((pk) => (
          <li key={pk.id} className="rounded-xl bg-white/[0.04] px-3 py-3">
            {editingId === pk.id ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <KeyRound className="text-muted-foreground h-5 w-5 shrink-0" />
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="h-7 min-w-0 flex-1 text-xs"
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                    autoFocus
                  />
                </div>
                <div className="flex justify-end gap-1.5">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 rounded-full border-white/20 bg-white px-2.5 text-xs font-medium text-black hover:bg-white/90"
                    onClick={() => setEditingId(null)}
                  >
                    {t('common.cancel')}
                  </Button>
                  <Button
                    size="sm"
                    className="h-7 rounded-full px-2.5 text-xs font-medium"
                    isLoading={renamePasskey.isPending}
                    onClick={() => {
                      if (editName.trim()) {
                        renamePasskey.mutate(
                          { id: pk.id, name: editName.trim() },
                          // handles on success
                          { onSuccess: () => setEditingId(null) },
                        )
                      }
                    }}
                  >
                    <RefreshCw className="h-3 w-3" />
                    {t('common.update')}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <KeyRound className="text-muted-foreground h-5 w-5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {pk.name ?? t('passkeys.unnamedPasskey')}
                  </p>
                  {pk.last_used_at && (
                    <p className="text-muted-foreground text-xs">
                      {t('passkeys.lastUsed', {
                        date: formatDate(pk.last_used_at, i18n.language),
                      })}
                    </p>
                  )}
                </div>
                <div className="flex gap-1">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={() => {
                      setEditingId(pk.id)
                      setEditName('')
                    }}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="text-destructive hover:text-destructive h-7 w-7"
                    isLoading={deletePasskey.isPending}
                    onClick={() => deletePasskey.mutate(pk.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>

      <div className="flex justify-end pt-1">
        <button
          onClick={() => registerPasskey.mutate()}
          disabled={registerPasskey.isPending}
          className="bg-primary flex h-9 items-center gap-2 rounded-full px-4 text-sm font-semibold text-white disabled:opacity-50"
        >
          <>
            <Plus className="h-3.5 w-3.5" />
            Add passkey
          </>
        </button>
      </div>
    </div>
  )
}
