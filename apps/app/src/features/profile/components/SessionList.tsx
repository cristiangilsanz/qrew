import { Monitor, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { useRevokeAllSessions } from '../hooks/useRevokeAllSessions'
import { useRevokeSession } from '../hooks/useRevokeSession'
import { useSessions } from '../hooks/useSessions'

export function SessionList() {
  const { t, i18n } = useTranslation()
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
    <div className="space-y-2">
      {sessions.length === 0 && <p className="text-muted-foreground py-4 text-center text-sm">—</p>}
      <ul className="space-y-1">
        {sessions.map((session) => (
          <li
            key={session.jti}
            className="flex items-center gap-3 rounded-xl bg-white/[0.04] px-3 py-3 text-sm"
          >
            <Monitor className="text-muted-foreground h-4 w-4 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white/80">
                {session.user_agent ?? t('profile.sessions.unknownDevice')}
              </p>
              <p className="text-muted-foreground text-xs">
                {session.ip_address ?? t('profile.sessions.unknownIp')} ·{' '}
                {t('profile.sessions.lastUsed', {
                  date: new Date(session.last_used_at).toLocaleDateString(i18n.language),
                })}
              </p>
            </div>
            <button
              onClick={() => revokeSession.mutate(session.jti)}
              disabled={revokeSession.isPending}
              className="text-muted-foreground hover:text-destructive shrink-0 disabled:opacity-40"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
      {sessions.length > 1 && (
        <div className="flex justify-end pt-1">
          <button
            onClick={() => revokeAll.mutate()}
            disabled={revokeAll.isPending}
            className="bg-destructive flex h-9 items-center gap-2 rounded-full px-4 text-sm font-semibold text-white disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t('profile.sessions.revokeAll')}
          </button>
        </div>
      )}
    </div>
  )
}
