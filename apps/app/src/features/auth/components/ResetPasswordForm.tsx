import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import type { AxiosError } from 'axios'
import { Eye, EyeOff, Lock, LogIn } from 'lucide-react'
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

import { type ApiErrorDetail, authApi, extractErrorMessage } from '../api'
import { AuthLayout } from './AuthLayout'

const schema = z.object({
  new_password: z.string().min(8),
})

type Values = z.infer<typeof schema>

interface Props {
  token: string
}

export function ResetPasswordForm({ token }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)

  const mutation = useMutation({
    mutationFn: (data: Values) => authApi.resetPassword(token, data.new_password),
    onSuccess: () => {
      toast.success(t('auth.resetPasswordSuccess'))
      navigate({ to: '/login' })
    },
    onError: (error: AxiosError<{ detail?: ApiErrorDetail }>) => {
      const message = extractErrorMessage(
        error.response?.data?.detail,
        t('auth.errors.resetFailed'),
      )
      toast.error(message)
    },
  })

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: '' },
  })

  return (
    <AuthLayout title={t('auth.resetPasswordTitle')} subtitle={t('auth.resetPasswordSubtitle')}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
          <FormField
            control={form.control}
            name="new_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth.newPassword')}</FormLabel>
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

          <Button type="submit" className="w-full rounded-full" isLoading={mutation.isPending}>
            <LogIn className="mr-2 h-4 w-4" />
            {t('auth.resetPasswordSubmit')}
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
