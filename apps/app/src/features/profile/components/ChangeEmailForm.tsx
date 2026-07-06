import { zodResolver } from '@hookform/resolvers/zod'
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

import { useChangeEmail } from '../hooks/useChangeEmail'

const schema = z.object({
  new_email: z.string().email(),
  current_password: z.string().min(1),
})

type Values = z.infer<typeof schema>

export function ChangeEmailForm() {
  const { t } = useTranslation()
  const [sent, setSent] = useState(false)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { new_email: '', current_password: '' },
  })

  const changeEmail = useChangeEmail(() => setSent(true))

  if (sent) {
    return (
      <div className="space-y-2">
        <h3 className="font-medium">{t('profile.changeEmail.title')}</h3>
        <p className="text-muted-foreground text-sm">{t('profile.changeEmail.success')}</p>
        <button className="text-primary text-sm hover:underline" onClick={() => setSent(false)}>
          {t('common.back')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="font-medium">{t('profile.changeEmail.title')}</h3>
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => changeEmail.mutate(v))} className="space-y-3">
          <FormField
            control={form.control}
            name="new_email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('profile.changeEmail.newEmail')}</FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="email" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('profile.changeEmail.currentPassword')}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" isLoading={changeEmail.isPending}>
            {t('profile.changeEmail.submit')}
          </Button>
        </form>
      </Form>
    </div>
  )
}
