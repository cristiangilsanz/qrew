// renders the email verification step component
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { Mail, MailCheck, RotateCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { type ApiErrorDetail, authApi } from '@/features/auth/api'
import { toastErrorMessage } from '@/lib/errors'

import { useVerifyEmail } from '../hooks/useVerifyEmail'

const schema = z.object({
  token: z.string().min(1),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
  email: string
}

const RESEND_COOLDOWN_SECONDS = 60

// renders the email verification step component
export function EmailVerificationStep({ onSuccess, email }: Props) {
  const { t } = useTranslation()
  const verify = useVerifyEmail(onSuccess)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((s) => s - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const resend = useMutation({
    // implements mutation fn
    mutationFn: () => authApi.resendEmailVerification(email),
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

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { token: '' },
  })

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Mail className="h-4 w-4 shrink-0" />
        <span>{t('auth.verifyEmail.sentTo', { email })}</span>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => verify.mutate(v))} className="space-y-4">
          <FormField
            control={form.control}
            name="token"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('onboarding.email.label')}</FormLabel>
                <FormControl>
                  <Input placeholder={t('onboarding.email.placeholder')} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full rounded-full" isLoading={verify.isPending}>
            <MailCheck className="mr-2 h-4 w-4" />
            {t('onboarding.email.submit')}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="w-full rounded-full"
            isLoading={resend.isPending}
            disabled={cooldown > 0}
            onClick={() => resend.mutate()}
          >
            <RotateCw className="mr-2 h-4 w-4" />
            {cooldown > 0
              ? t('common.waitSeconds', { seconds: cooldown })
              : t('auth.verifyEmail.resend')}
          </Button>
        </form>
      </Form>
    </div>
  )
}
