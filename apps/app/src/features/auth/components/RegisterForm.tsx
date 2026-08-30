// renders the register form component
import { zodResolver } from '@hookform/resolvers/zod'
import { Turnstile } from '@marsidev/react-turnstile'
import { Link, useNavigate } from '@tanstack/react-router'
import { Eye, EyeOff, Lock, Mail, Phone, User, UserPlus } from 'lucide-react'
import { useRef, useState } from 'react'
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
import { env } from '@/config/env'
import { DEFAULT_DIAL_ISO, DIAL_CODES, toE164 } from '@/lib/dialCodes'

import { useLogin } from '../hooks/useLogin'
import { useRegister } from '../hooks/useRegister'
import { AuthLayout } from './AuthLayout'

const registerSchema = z.object({
  full_name: z.string().min(2).max(255),
  email: z.string().email(),
  phone_number: z.string().min(7).max(20),
  password: z.string().min(8),
  terms_accepted: z
    .boolean()
    .refine((v) => v === true, { message: 'You must accept the terms and conditions' }),
  captcha_token: z.string().min(1),
})

type RegisterFormValues = z.infer<typeof registerSchema>

// renders the register form component
export function RegisterForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const register = useRegister()
  const [showPassword, setShowPassword] = useState(false)
  const turnstileRef = useRef<{ reset: () => void }>(null)
  const login = useLogin()
  const [dialIso, setDialIso] = useState(DEFAULT_DIAL_ISO)
  const [nationalNumber, setNationalNumber] = useState('')

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      email: '',
      phone_number: '',
      password: '',
      terms_accepted: false,
      captcha_token: '',
    },
  })

  // handles on submit
  const onSubmit = async (values: RegisterFormValues) => {
    try {
      await register.mutateAsync(values)
    } catch {
      turnstileRef.current?.reset()
      form.setValue('captcha_token', '')
      return
    }
    toast.success(t('auth.registrationSuccess'))
    // signing in straight away lands the new account on the first setup step
    try {
      const session = await login.mutateAsync({
        email: values.email,
        password: values.password,
      })
      await navigate({ to: session.setup_required ? '/setup' : '/home' })
    } catch {
      await navigate({ to: '/login' })
    }
  }

  return (
    <AuthLayout title={t('auth.register')} subtitle={t('auth.registerSubtitle')}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => void onSubmit(v))} className="space-y-4">
          <FormField
            control={form.control}
            name="full_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.fullName')}</FormLabel>
                <div className="relative">
                  <User className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                  <FormControl>
                    <Input autoComplete="name" className="pl-9" {...field} />
                  </FormControl>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

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
            name="phone_number"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.phoneNumber')}</FormLabel>
                <div className="flex gap-2">
                  <select
                    value={dialIso}
                    onChange={(e) => {
                      setDialIso(e.target.value)
                      field.onChange(toE164(e.target.value, nationalNumber))
                    }}
                    aria-label={t('auth.dialCode')}
                    className="border-input bg-background text-foreground w-24 shrink-0 rounded-md border px-2 py-2 text-sm focus:outline-none"
                  >
                    {DIAL_CODES.map((code) => (
                      <option key={code.iso} value={code.iso}>
                        {code.flag} {code.dial}
                      </option>
                    ))}
                  </select>
                  <div className="relative flex-1">
                    <Phone className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                    <FormControl>
                      <Input
                        type="tel"
                        autoComplete="tel-national"
                        inputMode="numeric"
                        className="pl-9"
                        value={nationalNumber}
                        onChange={(e) => {
                          const national = e.target.value
                          setNationalNumber(national)
                          field.onChange(toE164(dialIso, national))
                        }}
                      />
                    </FormControl>
                  </div>
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
                      autoComplete="new-password"
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

          <FormField
            control={form.control}
            name="terms_accepted"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-start gap-2">
                  <FormControl>
                    <input
                      id="terms_accepted"
                      type="checkbox"
                      className="border-border accent-primary mt-0.5 h-4 w-4 shrink-0 rounded"
                      checked={field.value}
                      onChange={(e) => field.onChange(e.target.checked)}
                    />
                  </FormControl>
                  <FormLabel
                    htmlFor="terms_accepted"
                    className="cursor-pointer leading-snug font-normal"
                  >
                    {t('auth.acceptTerms')}
                  </FormLabel>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="flex justify-center">
            <Turnstile
              ref={turnstileRef}
              siteKey={env.TURNSTILE_SITE_KEY}
              options={{ theme: 'dark', size: 'normal', language: 'en' }}
              onSuccess={(token) => form.setValue('captcha_token', token)}
            />
          </div>

          <Button
            type="submit"
            className="w-full rounded-full"
            isLoading={register.isPending}
            disabled={!form.watch('captcha_token')}
          >
            <UserPlus className="mr-2 h-4 w-4" />
            {t('auth.register')}
          </Button>
        </form>
      </Form>

      <p className="text-muted-foreground mt-4 text-center text-sm">
        {t('auth.hasAccount')}{' '}
        <Link to="/login" className="text-primary font-medium hover:underline">
          {t('auth.login')}
        </Link>
      </p>
    </AuthLayout>
  )
}
