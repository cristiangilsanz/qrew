import { zodResolver } from '@hookform/resolvers/zod'
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
}

export function PhoneVerificationStep({ onSuccess }: Props) {
  const { t } = useTranslation()
  const phoneNumber = useAuthStore((s) => s.phoneNumber)
  const verify = useVerifyPhone(onSuccess)
  const resend = useResendPhoneOtp()

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { otp: '' },
  })

  const onSubmit = (values: FormValues) => {
    verify.mutate({ phone_number: phoneNumber ?? '', otp: values.otp })
  }

  const handleResend = () => {
    if (phoneNumber) resend.mutate({ phone_number: phoneNumber })
  }

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground text-sm">{t('onboarding.phone.description')}</p>

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
          <Button type="submit" className="w-full" isLoading={verify.isPending}>
            {t('onboarding.phone.submit')}
          </Button>
        </form>
      </Form>

      <div className="text-center">
        <button
          type="button"
          onClick={handleResend}
          disabled={resend.isPending || !phoneNumber}
          className="text-primary text-sm hover:underline disabled:opacity-50"
        >
          {t('onboarding.phone.resend')}
        </button>
      </div>
    </div>
  )
}
