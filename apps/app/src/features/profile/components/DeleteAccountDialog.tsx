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

import { useDeleteAccount } from '../hooks/useDeleteAccount'

const schema = z.object({
  current_password: z.string().min(1),
})

type Values = z.infer<typeof schema>

export function DeleteAccountDialog() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: '' },
  })

  const deleteAccount = useDeleteAccount()

  if (!open) {
    return (
      <div className="space-y-1">
        <p className="text-muted-foreground text-sm">{t('profile.deleteAccount.description')}</p>
        <Button variant="destructive" onClick={() => setOpen(true)}>
          {t('profile.deleteAccount.button')}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground text-sm">{t('profile.deleteAccount.description')}</p>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((v) => deleteAccount.mutate(v.current_password))}
          className="space-y-3"
        >
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('profile.deleteAccount.currentPassword')}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="flex gap-2">
            <Button type="submit" variant="destructive" isLoading={deleteAccount.isPending}>
              {t('profile.deleteAccount.confirm')}
            </Button>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              {t('profile.deleteAccount.cancel')}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
