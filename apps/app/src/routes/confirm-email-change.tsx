import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { profileApi } from '@/features/profile/api'

export const Route = createFileRoute('/confirm-email-change')({
  validateSearch: (search: Record<string, unknown>) => ({
    token: typeof search.token === 'string' ? search.token : '',
  }),
  component: ConfirmEmailChangePage,
})

function ConfirmEmailChangePage() {
  const { t } = useTranslation()
  const { token } = Route.useSearch()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      return
    }
    profileApi
      .confirmEmailChange(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [token])

  return (
    <div className="text-foreground flex min-h-screen items-center justify-center p-6">
      <div className="max-w-sm space-y-4 text-center">
        {status === 'loading' && <p>{t('common.loading')}</p>}
        {status === 'success' && (
          <>
            <p className="text-lg font-semibold">{t('profile.changeEmail.confirmTitle')}</p>
            <p className="text-muted-foreground text-sm">
              {t('profile.changeEmail.confirmDescription')}
            </p>
            <button
              onClick={() => void navigate({ to: '/profile' })}
              className="text-primary text-sm hover:underline"
            >
              {t('profile.backToProfile')}
            </button>
          </>
        )}
        {status === 'error' && (
          <>
            <p className="text-destructive font-semibold">
              {t('profile.changeEmail.confirmError')}
            </p>
            <button
              onClick={() => void navigate({ to: '/profile' })}
              className="text-primary text-sm hover:underline"
            >
              {t('profile.backToProfile')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
