// renders the invite member form component
import { zodResolver } from '@hookform/resolvers/zod'
import { Info } from 'lucide-react'
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
import { cn } from '@/lib/utils'

import { useInviteCollaborator } from '../hooks/useInviteCollaborator'

const schema = z.object({
  email: z.string().email(),
  role: z.enum(['member', 'manager']),
})

type Values = z.infer<typeof schema>

interface Props {
  orgId: string
  onSuccess?: () => void
}

// renders the invite member form component
export function InviteCollaboratorForm({ orgId, onSuccess }: Props) {
  const { t } = useTranslation()

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', role: 'member' },
  })

  const invite = useInviteCollaborator(orgId)

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          invite.mutate(v, {
            // handles on success
            onSuccess: () => {
              form.reset()
              onSuccess?.()
            },
          })
        })}
        className="w-full space-y-4"
      >
        {/* the invitation travels by address, so the form never reads the directory
            and an owner or manager needs no platform wide permission to send it */}
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.collaborators.emailLabel')}</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  autoComplete="off"
                  placeholder={t('organiser.collaborators.emailPlaceholder')}
                  {...field}
                />
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
              <FormLabel>{t('organiser.collaborators.roleLabel')}</FormLabel>
              <FormControl>
                <div className="grid grid-cols-2 items-stretch gap-2">
                  {(['manager', 'member'] as const).map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => field.onChange(role)}
                      className={cn(
                        'flex h-full flex-col rounded-xl border p-3 text-left transition-colors',
                        field.value === role
                          ? 'border-primary bg-primary/10'
                          : 'border-white/10 bg-white/5 hover:bg-white/[0.08]',
                      )}
                    >
                      <p className="text-sm font-semibold capitalize">{role}</p>
                      <p className="text-muted-foreground mt-0.5 text-xs leading-tight">
                        {t(
                          `organiser.collaborators.role${role.charAt(0).toUpperCase() + role.slice(1)}Desc`,
                        )}
                      </p>
                    </button>
                  ))}
                </div>
              </FormControl>
              <p className="text-muted-foreground mt-2 flex items-center gap-1.5 text-xs">
                <Info className="h-3 w-3 shrink-0 opacity-60" />
                {t('organiser.collaborators.roleValidationNote')}
              </p>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Button type="submit" isLoading={invite.isPending}>
            {t('organiser.collaborators.inviteButton')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
