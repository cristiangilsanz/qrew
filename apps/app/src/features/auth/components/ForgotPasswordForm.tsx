import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Mail, Send } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
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

import { authApi } from '../api'
import { AuthLayout } from './AuthLayout'

const schema = z.object({
  email: z.string().email(),
})

type Values = z.infer<typeof schema>

export function ForgotPasswordForm() {
  const { t } = useTranslation()
  const [sent, setSent] = useState(false)

  const mutation = useMutation({
    mutationFn: (data: Values) => authApi.forgotPassword(data.email),
    onSuccess: () => setSent(true),
  })

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: '' },
  })

  if (sent) {
    return (
      <AuthLayout title={t('auth.forgotPasswordTitle')} subtitle={t('auth.forgotPasswordSuccess')}>
        <p className="text-muted-foreground text-center text-sm">
          <Link to="/login" className="text-primary font-medium hover:underline">
            {t('auth.login')}
          </Link>
        </p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title={t('auth.forgotPasswordTitle')}
      subtitle={t('auth.forgotPasswordSubtitle')}
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.email')}</FormLabel>
                <div className="relative">
                  <Mail className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                  <FormControl>
                    <Input
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      className="pl-9"
                      {...field}
                    />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" className="w-full rounded-full" isLoading={mutation.isPending}>
            <Send className="mr-2 h-4 w-4" />
            {t('auth.forgotPasswordSubmit')}
          </Button>
        </form>
      </Form>

      <p className="text-muted-foreground mt-4 text-center text-sm">
        {t('auth.rememberedPassword')}{' '}
        <Link to="/login" className="text-primary font-medium hover:underline">
          {t('auth.login')}
        </Link>
      </p>
    </AuthLayout>
  )
}
