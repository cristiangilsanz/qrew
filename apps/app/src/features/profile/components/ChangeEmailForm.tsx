import { zodResolver } from '@hookform/resolvers/zod'
import { Send } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

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

interface Props {
  hideTitle?: boolean
}

const darkInput =
  'border-white/5 bg-black/30 text-white/70 placeholder:text-white/15 focus-visible:border-white/15 focus-visible:ring-0 focus-visible:ring-offset-0'

export function ChangeEmailForm({ hideTitle }: Props) {
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
        {!hideTitle && <h3 className="font-medium">{t('profile.changeEmail.title')}</h3>}
        <p className="text-muted-foreground text-sm">{t('profile.changeEmail.success')}</p>
        <button className="text-primary text-sm hover:underline" onClick={() => setSent(false)}>
          {t('common.back')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {!hideTitle && <h3 className="font-medium">{t('profile.changeEmail.title')}</h3>}
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => changeEmail.mutate(v))} className="space-y-3">
          <FormField
            control={form.control}
            name="new_email"
            render={({ field }) => (
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.changeEmail.newEmail')}
                </FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="email" className={darkInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.changeEmail.currentPassword')}
                </FormLabel>
                <FormControl>
                  <Input
                    type="password"
                    autoComplete="current-password"
                    className={darkInput}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={changeEmail.isPending}
              className="bg-primary flex h-10 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {changeEmail.isPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  {t('profile.changeEmail.submit')}
                </>
              )}
            </button>
          </div>
        </form>
      </Form>
    </div>
  )
}
