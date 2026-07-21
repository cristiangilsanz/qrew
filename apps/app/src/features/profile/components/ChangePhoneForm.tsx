import { zodResolver } from '@hookform/resolvers/zod'
import { Check, Send } from 'lucide-react'
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

import { useChangePhone } from '../hooks/useChangePhone'
import { useConfirmPhoneChange } from '../hooks/useConfirmPhoneChange'

const step1Schema = z.object({
  new_phone_number: z.string().min(7),
  current_password: z.string().min(1),
})

const step2Schema = z.object({
  otp: z.string().length(6),
})

type Step1Values = z.infer<typeof step1Schema>
type Step2Values = z.infer<typeof step2Schema>

interface Props {
  hideTitle?: boolean
}

const darkInput =
  'border-white/5 bg-black/30 text-white/70 placeholder:text-white/15 focus-visible:border-white/15 focus-visible:ring-0 focus-visible:ring-offset-0'

export function ChangePhoneForm({ hideTitle }: Props) {
  const { t } = useTranslation()
  const [pendingPhone, setPendingPhone] = useState<string | null>(null)

  const step1Form = useForm<Step1Values>({
    resolver: zodResolver(step1Schema),
    defaultValues: { new_phone_number: '', current_password: '' },
  })

  const step2Form = useForm<Step2Values>({
    resolver: zodResolver(step2Schema),
    defaultValues: { otp: '' },
  })

  const changePhone = useChangePhone()
  const confirmPhone = useConfirmPhoneChange(() => {
    setPendingPhone(null)
    step1Form.reset()
    step2Form.reset()
  })

  if (pendingPhone) {
    return (
      <div className="space-y-4">
        {!hideTitle && <h3 className="font-medium">{t('profile.changePhone.title')}</h3>}
        <p className="text-muted-foreground text-sm">{t('profile.changePhone.otpSent')}</p>
        <Form {...step2Form}>
          <form
            onSubmit={step2Form.handleSubmit((v) =>
              confirmPhone.mutate({ new_phone_number: pendingPhone, otp: v.otp }),
            )}
            className="space-y-3"
          >
            <FormField
              control={step2Form.control}
              name="otp"
              render={({ field }) => (
                <FormItem className="space-y-1.5">
                  <FormLabel className="text-muted-foreground text-xs">
                    {t('profile.changePhone.otp')}
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="123456"
                      autoComplete="one-time-code"
                      className={darkInput}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                className="text-muted-foreground text-sm hover:text-white"
                onClick={() => setPendingPhone(null)}
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={confirmPhone.isPending}
                className="bg-primary flex h-10 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white disabled:opacity-50"
              >
                {confirmPhone.isPending ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    {t('profile.changePhone.confirmSubmit')}
                  </>
                )}
              </button>
            </div>
          </form>
        </Form>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {!hideTitle && <h3 className="font-medium">{t('profile.changePhone.title')}</h3>}
      <Form {...step1Form}>
        <form
          onSubmit={step1Form.handleSubmit((v) =>
            changePhone.mutate(v, {
              onSuccess: () => setPendingPhone(v.new_phone_number),
            }),
          )}
          className="space-y-3"
        >
          <FormField
            control={step1Form.control}
            name="new_phone_number"
            render={({ field }) => (
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.changePhone.newPhone')}
                </FormLabel>
                <FormControl>
                  <Input type="tel" autoComplete="tel" className={darkInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={step1Form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem className="space-y-1.5">
                <FormLabel className="text-muted-foreground text-xs">
                  {t('profile.changePhone.currentPassword')}
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
              disabled={changePhone.isPending}
              className="bg-primary flex h-10 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {changePhone.isPending ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  {t('profile.changePhone.submit')}
                </>
              )}
            </button>
          </div>
        </form>
      </Form>
    </div>
  )
}
