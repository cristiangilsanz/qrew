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

export function ChangePhoneForm() {
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
        <h3 className="font-medium">{t('profile.changePhone.title')}</h3>
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
                <FormItem>
                  <FormLabel>{t('profile.changePhone.otp')}</FormLabel>
                  <FormControl>
                    <Input placeholder="123456" autoComplete="one-time-code" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex gap-2">
              <Button type="submit" isLoading={confirmPhone.isPending}>
                {t('profile.changePhone.confirmSubmit')}
              </Button>
              <Button type="button" variant="outline" onClick={() => setPendingPhone(null)}>
                {t('common.cancel')}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="font-medium">{t('profile.changePhone.title')}</h3>
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
              <FormItem>
                <FormLabel>{t('profile.changePhone.newPhone')}</FormLabel>
                <FormControl>
                  <Input type="tel" autoComplete="tel" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={step1Form.control}
            name="current_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('profile.changePhone.currentPassword')}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" isLoading={changePhone.isPending}>
            {t('profile.changePhone.submit')}
          </Button>
        </form>
      </Form>
    </div>
  )
}
