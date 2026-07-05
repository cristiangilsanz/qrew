import { zodResolver } from '@hookform/resolvers/zod'
import { Mail } from 'lucide-react'
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

import { useVerifyEmail } from '../hooks/useVerifyEmail'

const schema = z.object({
  token: z.string().min(1),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
}

export function EmailVerificationStep({ onSuccess }: Props) {
  const { t } = useTranslation()
  const verify = useVerifyEmail(onSuccess)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { token: '' },
  })

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Mail className="h-4 w-4 shrink-0" />
        <span>{t('onboarding.email.description')}</span>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => verify.mutate(v))} className="space-y-4">
          <FormField
            control={form.control}
            name="token"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('onboarding.email.label')}</FormLabel>
                <FormControl>
                  <Input placeholder={t('onboarding.email.placeholder')} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full" isLoading={verify.isPending}>
            {t('onboarding.email.submit')}
          </Button>
        </form>
      </Form>
    </div>
  )
}
