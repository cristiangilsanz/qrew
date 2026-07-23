import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from '@tanstack/react-router'
import { Eye, EyeOff, Lock, Mail, Phone, User, UserPlus } from 'lucide-react'
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
})

type RegisterFormValues = z.infer<typeof registerSchema>

export function RegisterForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const register = useRegister()
  const [showPassword, setShowPassword] = useState(false)

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      email: '',
      phone_number: '',
      password: '',
      terms_accepted: false,
    },
  })

  const onSubmit = (values: RegisterFormValues) => {
    register.mutate(values, {
      onSuccess: () => {
        toast.success(t('auth.registrationSuccess'))
        navigate({ to: '/login' })
      },
    })
  }

  return (
    <AuthLayout title={t('auth.register')} subtitle={t('auth.registerSubtitle')}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="full_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.fullName')}</FormLabel>
                <div className="relative">
                  <User className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                  <FormControl>
                    <Input
                      autoComplete="name"
                      placeholder={t('auth.fullNamePlaceholder')}
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
                <div className="relative">
                  <Phone className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
                  <FormControl>
                    <Input
                      type="tel"
                      autoComplete="tel"
                      placeholder="+34 612 345 678"
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

          <Button type="submit" className="w-full rounded-full" isLoading={register.isPending}>
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
