import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { zodResolver } from '@hookform/resolvers/zod'
import { ShieldCheck } from 'lucide-react'
import { useState } from 'react'
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
import { AuthLayout } from '@/features/auth/components/AuthLayout'
import { totpApi } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth/verify-totp')({
  component: VerifyTotpPage,
})

const schema = z.object({
  code: z.string().min(6).max(10),
})
type FormValues = z.infer<typeof schema>

function VerifyTotpPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const totpToken = useAuthStore((s) => s.totpToken)
  const setTokens = useAuthStore((s) => s.setTokens)
  const clearTotpPending = useAuthStore((s) => s.clearTotpPending)
  const [isLoading, setIsLoading] = useState(false)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { code: '' },
  })

  const onSubmit = async (values: FormValues) => {
    if (!totpToken) {
      void navigate({ to: '/login' })
      return
    }
    setIsLoading(true)
    try {
      const data = await totpApi.verify(totpToken, values.code)
      setTokens(data.access_token, data.refresh_token)
      clearTotpPending()
      void navigate({ to: '/home' })
    } catch {
      toast.error(t('auth.totp.invalidCode'))
      form.setError('code', { message: t('auth.totp.invalidCode') })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthLayout title={t('auth.totp.title')} subtitle={t('auth.totp.subtitle')}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.totp.codeLabel')}</FormLabel>
                <div className="relative">
                  <ShieldCheck className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                  <FormControl>
                    <Input
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      placeholder="000000"
                      maxLength={10}
                      className="pl-9 font-mono tracking-widest"
                      {...field}
                    />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" className="w-full rounded-full" isLoading={isLoading}>
            <ShieldCheck className="mr-2 h-4 w-4" />
            {t('auth.totp.verify')}
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
