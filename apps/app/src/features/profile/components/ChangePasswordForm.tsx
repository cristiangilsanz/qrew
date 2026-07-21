import { zodResolver } from '@hookform/resolvers/zod'
import { Eye, EyeOff, RefreshCw } from 'lucide-react'
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

import { useChangePassword } from '../hooks/useChangePassword'

const schema = z.object({
  current_password: z.string().min(1),
  new_password: z.string().min(8),
})

type Values = z.infer<typeof schema>

interface Props {
  hideTitle?: boolean
}

const darkInput =
  'border-white/5 bg-black/30 text-white/70 placeholder:text-white/15 focus-visible:border-white/15 focus-visible:ring-0 focus-visible:ring-offset-0'

export function ChangePasswordForm({ hideTitle }: Props) {
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
      {!hideTitle && <h3 className="font-medium">{t('profile.changePassword.title')}</h3>}
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => changePassword.mutate(v))} className="space-y-3">
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.changePassword.currentPassword')}
                </FormLabel>
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showCurrent ? 'text' : 'password'}
                      autoComplete="current-password"
                      className={`${darkInput} pr-10`}
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowCurrent((v) => !v)}
                    className="text-muted-foreground absolute top-1/2 right-3 -translate-y-1/2 hover:text-white"
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
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.changePassword.newPassword')}
                </FormLabel>
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showNew ? 'text' : 'password'}
                      autoComplete="new-password"
                      className={`${darkInput} pr-10`}
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowNew((v) => !v)}
                    className="text-muted-foreground absolute top-1/2 right-3 -translate-y-1/2 hover:text-white"
                    tabIndex={-1}
                  >
                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={changePassword.isPending}
              className="bg-primary flex h-10 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {changePassword.isPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5" />
                  {t('profile.changePassword.submit')}
                </>
              )}
            </button>
          </div>
        </form>
      </Form>
    </div>
  )
}
