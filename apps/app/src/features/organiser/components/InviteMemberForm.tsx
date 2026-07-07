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

import { useInviteMember } from '../hooks/useInviteMember'

const schema = z.object({
  email: z.string().email(),
  role: z.enum(['member', 'manager']),
})

type Values = z.infer<typeof schema>

interface Props {
  orgId: string
}

export function InviteMemberForm({ orgId }: Props) {
  const { t } = useTranslation()

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', role: 'member' },
  })

  const invite = useInviteMember(orgId)

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          invite.mutate(v)
          form.reset()
        })}
        className="space-y-3"
      >
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.members.emailLabel')}</FormLabel>
              <FormControl>
                <Input type="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="role"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.members.roleLabel')}</FormLabel>
              <FormControl>
                <select
                  className="border-input bg-background ring-offset-background focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  {...field}
                >
                  <option value="member">Member</option>
                  <option value="manager">Manager</option>
                </select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" isLoading={invite.isPending}>
          {t('organiser.members.inviteButton')}
        </Button>
      </form>
    </Form>
  )
}
