// implements verify email
import { useMutation } from '@tanstack/react-query'
import { createFileRoute, Link, useSearch } from '@tanstack/react-router'
import type { AxiosError } from 'axios'
import { CircleX, Loader2, MailCheck } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { type ApiErrorDetail, authApi } from '@/features/auth/api'
import { AuthLayout } from '@/features/auth/components/AuthLayout'
import { onboardingApi } from '@/features/onboarding/api'
import { toastErrorMessage } from '@/lib/errors'

const searchSchema = z.object({
  email: z.string().optional(),
  token: z.string().optional(),
})

export const Route = createFileRoute('/_auth/verify-email')({
  validateSearch: searchSchema,
  component: VerifyEmailPage,
})

const RESEND_COOLDOWN_SECONDS = 60

// confirms the address when the mailed link is opened and otherwise waits for it
function VerifyEmailPage() {
  const { t } = useTranslation()
  const { email, token } = useSearch({ from: '/_auth/verify-email' })
  const [cooldown, setCooldown] = useState(0)
  const confirmedRef = useRef(false)

  const confirm = useMutation({
    // implements mutation fn
    mutationFn: (value: string) => onboardingApi.verifyEmail({ token: value }),
  })

  useEffect(() => {
    if (!token || confirmedRef.current) return
    confirmedRef.current = true
    confirm.mutate(token)
  }, [token, confirm])

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((s) => s - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const resend = useMutation({
    // implements mutation fn
    mutationFn: () => authApi.resendEmailVerification(email ?? ''),
    // handles on success
    onSuccess: () => {
      toast.success(t('auth.verifyEmail.resent'))
      setCooldown(RESEND_COOLDOWN_SECONDS)
    },
    // handles on error
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      toast.error(toastErrorMessage(error, t('auth.verifyEmail.resendFailed')))
      setCooldown(RESEND_COOLDOWN_SECONDS)
    },
  })

  if (token) {
    return (
      <AuthLayout>
        <div className="space-y-4 pt-6 pb-4 text-center">
          {confirm.isPending && (
            <>
              <Loader2 className="text-primary mx-auto h-10 w-10 animate-spin" />
              <p className="text-muted-foreground text-sm">{t('auth.verifyEmail.confirming')}</p>
            </>
          )}
          {confirm.isSuccess && (
            <>
              <MailCheck className="mx-auto h-10 w-10 text-green-400" />
              <p className="text-base font-semibold">{t('auth.verifyEmail.confirmed')}</p>
            </>
          )}
          {confirm.isError && (
            <>
              <CircleX className="text-destructive mx-auto h-10 w-10" />
              <p className="text-base font-semibold">{t('auth.verifyEmail.linkExpired')}</p>
            </>
          )}
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title={t('auth.verifyEmail.title')}>
      <div className="space-y-5 text-center">
        <MailCheck className="text-primary mx-auto h-10 w-10" />
        <p className="text-muted-foreground text-sm">
          {email ? t('auth.verifyEmail.sentTo', { email }) : t('auth.verifyEmail.sent')}
        </p>
        <p className="text-muted-foreground text-xs">{t('auth.verifyEmail.spamHint')}</p>

        {email && (
          <Button
            type="button"
            variant="outline"
            className="w-full rounded-full"
            isLoading={resend.isPending}
            disabled={cooldown > 0}
            onClick={() => resend.mutate()}
          >
            {cooldown > 0
              ? t('common.waitSeconds', { seconds: cooldown })
              : t('auth.verifyEmail.resend')}
          </Button>
        )}

        <Link to="/login" className="text-primary block text-sm underline">
          {t('auth.verifyEmail.backToLogin')}
        </Link>
      </div>
    </AuthLayout>
  )
}
