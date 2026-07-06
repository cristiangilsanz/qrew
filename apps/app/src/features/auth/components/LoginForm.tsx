import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from '@tanstack/react-router'
import { Eye, EyeOff, KeyRound, Lock, Mail } from 'lucide-react'
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

import { useLogin } from '../hooks/useLogin'
import { usePasskeyLogin } from '../hooks/usePasskeyLogin'
import { AuthLayout } from './AuthLayout'

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const login = useLogin()
  const passkeyLogin = usePasskeyLogin()
  const [showPassword, setShowPassword] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = (values: LoginFormValues) => {
    login.mutate(values, {
      onSuccess: (data) => navigate({ to: data.setup_required ? '/setup' : '/events' }),
    })
  }

  const onPasskeyLogin = () => {
    const email = form.getValues('email')
    if (!email) {
      form.setError('email', { message: t('auth.emailRequiredForPasskey') })
      return
    }
    passkeyLogin.mutate(email, {
      onSuccess: (data) => navigate({ to: data.setup_required ? '/setup' : '/events' }),
    })
  }

  return (
    <AuthLayout title={t('auth.login')} subtitle={t('auth.loginSubtitle')}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
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

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.password')}</FormLabel>
                <div className="relative">
                  <Lock className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                  <FormControl>
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      placeholder="••••••••"
                      className="pr-10 pl-9"
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" className="w-full" isLoading={login.isPending}>
            {t('auth.login')}
          </Button>
        </form>
      </Form>

      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center">
          <span className="border-border w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background text-muted-foreground px-2">{t('auth.or')}</span>
        </div>
      </div>

      <Button
        type="button"
        variant="outline"
        className="w-full"
        isLoading={passkeyLogin.isPending}
        onClick={onPasskeyLogin}
      >
        <KeyRound className="mr-2 h-4 w-4" />
        {t('auth.passkeyLogin')}
      </Button>

      <p className="text-muted-foreground mt-4 text-center text-sm">
        {t('auth.noAccount')}{' '}
        <Link to="/register" className="text-primary font-medium hover:underline">
          {t('auth.register')}
        </Link>
      </p>
    </AuthLayout>
  )
}
