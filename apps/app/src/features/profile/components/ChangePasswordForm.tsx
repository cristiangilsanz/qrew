import { zodResolver } from '@hookform/resolvers/zod'
import { Eye, EyeOff } from 'lucide-react'
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

import { useChangePassword } from '../hooks/useChangePassword'

const schema = z.object({
  current_password: z.string().min(1),
  new_password: z.string().min(8),
})

type Values = z.infer<typeof schema>

export function ChangePasswordForm() {
  const { t } = useTranslation()
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: '', new_password: '' },
  })

  const changePassword = useChangePassword(() => form.reset())

  return (
    <div className="space-y-4">
      <h3 className="font-medium">{t('profile.changePassword.title')}</h3>
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => changePassword.mutate(v))} className="space-y-3">
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('profile.changePassword.currentPassword')}</FormLabel>
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showCurrent ? 'text' : 'password'}
                      autoComplete="current-password"
                      className="pr-10"
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowCurrent((v) => !v)}
                    className="text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2"
                    tabIndex={-1}
                  >
                    {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="new_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('profile.changePassword.newPassword')}</FormLabel>
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showNew ? 'text' : 'password'}
                      autoComplete="new-password"
                      className="pr-10"
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowNew((v) => !v)}
                    className="text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2"
                    tabIndex={-1}
                  >
                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" isLoading={changePassword.isPending}>
            {t('profile.changePassword.submit')}
          </Button>
        </form>
      </Form>
    </div>
  )
}
