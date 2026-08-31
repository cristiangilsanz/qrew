// renders the phone verification step component
import { zodResolver } from '@hookform/resolvers/zod'
import { RotateCw, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
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
import { useAuthStore } from '@/store/auth'

import { useResendPhoneOtp } from '../hooks/useResendPhoneOtp'
import { useVerifyPhone } from '../hooks/useVerifyPhone'

const schema = z.object({
  otp: z.string().regex(/^\d{6}$/, 'Enter a 6-digit code'),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
  phoneNumber: string
}

// renders the phone verification step component
export function PhoneVerificationStep({ onSuccess, phoneNumber: fromStatus }: Props) {
  const { t } = useTranslation()
  // the store only knows the number when the account was created in this session
  const remembered = useAuthStore((s) => s.phoneNumber)
  const phoneNumber = fromStatus || (remembered ?? '')
  const verify = useVerifyPhone(onSuccess)
  const resend = useResendPhoneOtp()
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((v) => v - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { otp: '' },
  })

  // handles on submit
  const onSubmit = (values: FormValues) => {
    verify.mutate({ phone_number: phoneNumber, otp: values.otp })
  }

  // handles handle resend
  const handleResend = () => {
    if (!phoneNumber) return
    resend.mutate({ phone_number: phoneNumber }, { onSettled: () => setCooldown(60) })
  }

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground text-sm">
        {t('onboarding.phone.sentTo', { phone: phoneNumber })}
      </p>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="otp"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('onboarding.phone.label')}</FormLabel>
                <FormControl>
                  <Input
                    placeholder={t('onboarding.phone.placeholder')}
                    maxLength={6}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full rounded-full" isLoading={verify.isPending}>
            <ShieldCheck className="mr-2 h-4 w-4" />
            {t('onboarding.phone.submit')}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="w-full rounded-full"
            isLoading={resend.isPending}
            disabled={!phoneNumber || cooldown > 0}
            onClick={handleResend}
          >
            <RotateCw className="mr-2 h-4 w-4" />
            {cooldown > 0
              ? t('common.waitSeconds', { seconds: cooldown })
              : t('onboarding.phone.resend')}
          </Button>
        </form>
      </Form>
    </div>
  )
}
