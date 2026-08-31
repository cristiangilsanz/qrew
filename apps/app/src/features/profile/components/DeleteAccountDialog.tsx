// renders the delete account dialog component
import { zodResolver } from '@hookform/resolvers/zod'
import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

import { ConfirmDialog } from '@/components/ui/confirm-dialog'
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

const schema = z.object({ current_password: z.string().min(1) })
type Values = z.infer<typeof schema>

const darkInput =
  'border-white/5 bg-black/30 text-white/70 placeholder:text-white/15 focus-visible:border-white/15 focus-visible:ring-0 focus-visible:ring-offset-0'

const COUNTDOWN = 10

// renders the delete account dialog component
export function DeleteAccountDialog() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: '' },
  })

  const deleteAccount = useDeleteAccount(() => setOpen(false))

  // closes the dialog and forgets whatever was typed into it
  const close = (next: boolean) => {
    setOpen(next)
    if (!next) form.reset()
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-white/5"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500/10">
          <Trash2 className="h-4 w-4 text-red-400" />
        </div>
        <span className="flex-1 text-sm font-semibold text-red-400">
          {t('profile.deleteAccount.button')}
        </span>
      </button>

      <ConfirmDialog
        open={open}
        onOpenChange={close}
        tone="destructive"
        icon={Trash2}
        title={t('profile.deleteAccount.title')}
        description={t('profile.deleteAccount.description')}
        irreversible
        confirmLabel={t('profile.deleteAccount.confirm')}
        isLoading={deleteAccount.isPending}
        countdownSeconds={COUNTDOWN}
        onConfirm={form.handleSubmit((v) => deleteAccount.mutate(v.current_password))}
      >
        <Form {...form}>
          <FormField
            control={form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.deleteAccount.currentPassword')}
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
        </Form>
      </ConfirmDialog>
    </>
  )
}
