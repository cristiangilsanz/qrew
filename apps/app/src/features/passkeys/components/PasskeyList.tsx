import { KeyRound, Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

import { useDeletePasskey } from '../hooks/useDeletePasskey'
import { usePasskeys } from '../hooks/usePasskeys'
import { useRenamePasskey } from '../hooks/useRenamePasskey'

export function PasskeyList() {
  const { t } = useTranslation()
  const { data, isLoading } = usePasskeys()
  const deletePasskey = useDeletePasskey()
  const renamePasskey = useRenamePasskey()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  const passkeys = data?.items ?? []

  if (passkeys.length === 0) {
    return (
      <div className="text-muted-foreground py-8 text-center text-sm">{t('passkeys.empty')}</div>
    )
  }

  return (
    <ul className="space-y-3">
      {passkeys.map((pk) => (
        <li
          key={pk.id}
          className="bg-card border-border flex items-center gap-3 rounded-lg border p-3"
        >
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
                      date: new Date(pk.last_used_at).toLocaleDateString(),
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
  )
}
