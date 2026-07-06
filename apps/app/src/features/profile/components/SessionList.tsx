import { Monitor, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import { useRevokeAllSessions } from '../hooks/useRevokeAllSessions'
import { useRevokeSession } from '../hooks/useRevokeSession'
import { useSessions } from '../hooks/useSessions'

export function SessionList() {
  const { t } = useTranslation()
  const { data, isLoading } = useSessions()
  const revokeSession = useRevokeSession()
  const revokeAll = useRevokeAllSessions()

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="border-primary h-6 w-6 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  const sessions = data?.items ?? []

  return (
    <div className="space-y-3">
      {sessions.length > 1 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            isLoading={revokeAll.isPending}
            onClick={() => revokeAll.mutate()}
          >
            {t('profile.sessions.revokeAll')}
          </Button>
        </div>
      )}
      {sessions.length === 0 && <p className="text-muted-foreground py-4 text-center text-sm">—</p>}
      <ul className="space-y-2">
        {sessions.map((session) => (
          <li
            key={session.jti}
            className="bg-muted/40 flex items-center gap-3 rounded-lg p-3 text-sm"
          >
            <Monitor className="text-muted-foreground h-4 w-4 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">
                {session.user_agent ?? t('profile.sessions.unknownDevice')}
              </p>
              <p className="text-muted-foreground text-xs">
                {session.ip_address ?? t('profile.sessions.unknownIp')} ·{' '}
                {t('profile.sessions.lastUsed', {
                  date: new Date(session.last_used_at).toLocaleDateString(),
                })}
              </p>
            </div>
            <Button
              size="icon"
              variant="ghost"
              className="text-destructive hover:text-destructive h-7 w-7 shrink-0"
              isLoading={revokeSession.isPending}
              onClick={() => revokeSession.mutate(session.jti)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
