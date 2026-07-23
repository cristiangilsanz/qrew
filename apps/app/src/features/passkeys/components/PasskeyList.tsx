import { useQueryClient } from '@tanstack/react-query'
import { KeyRound, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useRegisterPasskey } from '@/features/onboarding/hooks/useRegisterPasskey'

import { useDeletePasskey } from '../hooks/useDeletePasskey'
import { usePasskeys } from '../hooks/usePasskeys'
import { useRenamePasskey } from '../hooks/useRenamePasskey'

export function PasskeyList() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const { data, isLoading } = usePasskeys()
  const deletePasskey = useDeletePasskey()
  const renamePasskey = useRenamePasskey()
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
          <li key={pk.id} className="flex items-center gap-3 rounded-xl bg-white/[0.04] px-3 py-3">
            <KeyRound className="text-muted-foreground h-5 w-5 shrink-0" />
            <div className="min-w-0 flex-1">
              {editingId === pk.id ? (
                <div className="flex gap-2">
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="h-7 text-sm"
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                    autoFocus
                  />
                  <Button
                    size="sm"
                    isLoading={renamePasskey.isPending}
                    onClick={() => {
                      if (editName.trim()) {
                        renamePasskey.mutate(
                          { id: pk.id, name: editName.trim() },
                          { onSuccess: () => setEditingId(null) },
                        )
                      }
                    }}
                  >
                    {t('common.save')}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>
                    {t('common.cancel')}
                  </Button>
                </div>
              ) : (
                <>
                  <p className="truncate text-sm font-medium">
                    {pk.name ?? t('passkeys.unnamedPasskey')}
                  </p>
                  {pk.last_used_at && (
                    <p className="text-muted-foreground text-xs">
                      {t('passkeys.lastUsed', {
                        date: new Date(pk.last_used_at).toLocaleDateString(i18n.language),
                      })}
                    </p>
                  )}
                </>
              )}
            </div>
            {editingId !== pk.id && (
              <div className="flex gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  onClick={() => {
                    setEditingId(pk.id)
                    setEditName(pk.name ?? '')
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
          {registerPasskey.isPending ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <>
              <Plus className="h-3.5 w-3.5" />
              Add passkey
            </>
          )}
        </button>
      </div>
    </div>
  )
}
