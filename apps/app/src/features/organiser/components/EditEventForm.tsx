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

import type { OrgEvent } from '../api'
import { useUpdateEvent } from '../hooks/useUpdateEvent'

const schema = z
  .object({
    name: z.string().min(1),
    description: z.string().optional(),
    starts_at: z.string().min(1),
    ends_at: z.string().min(1),
    sale_starts_at: z.string().min(1),
    sale_ends_at: z.string().min(1),
    max_tickets_per_user: z.coerce.number().int().min(1).max(20),
  })
  .refine((v) => new Date(v.ends_at) > new Date(v.starts_at), {
    message: 'End time must be after start time',
    path: ['ends_at'],
  })
  .refine((v) => new Date(v.sale_ends_at) <= new Date(v.starts_at), {
    message: 'Sale must end before or at event start',
    path: ['sale_ends_at'],
  })

type Values = z.infer<typeof schema>

interface Props {
  event: OrgEvent
  orgId: string
}

export function EditEventForm({ event, orgId }: Props) {
  const { t } = useTranslation()

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: event.name,
      description: event.description ?? '',
      starts_at: new Date(event.starts_at).toISOString().slice(0, 16),
      ends_at: new Date(event.ends_at).toISOString().slice(0, 16),
      sale_starts_at: new Date(event.sale_starts_at).toISOString().slice(0, 16),
      sale_ends_at: new Date(event.sale_ends_at).toISOString().slice(0, 16),
      max_tickets_per_user: event.max_tickets_per_user,
    },
  })

  const updateEvent = useUpdateEvent(orgId, event.id)

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) =>
          updateEvent.mutate({
            ...v,
            starts_at: new Date(v.starts_at).toISOString(),
            ends_at: new Date(v.ends_at).toISOString(),
            sale_starts_at: new Date(v.sale_starts_at).toISOString(),
            sale_ends_at: new Date(v.sale_ends_at).toISOString(),
          }),
        )}
        className="space-y-3"
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.events.nameLabel')}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.events.descriptionLabel')}</FormLabel>
              <FormControl>
                <textarea
                  rows={3}
                  className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex min-h-[60px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="starts_at"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.events.startsAtLabel')}</FormLabel>
                <FormControl>
                  <Input type="datetime-local" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="ends_at"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.events.endsAtLabel')}</FormLabel>
                <FormControl>
                  <Input type="datetime-local" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="sale_starts_at"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.events.saleStartsAtLabel')}</FormLabel>
                <FormControl>
                  <Input type="datetime-local" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="sale_ends_at"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.events.saleEndsAtLabel')}</FormLabel>
                <FormControl>
                  <Input type="datetime-local" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="max_tickets_per_user"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.events.maxTicketsLabel')}</FormLabel>
              <FormControl>
                <Input type="number" min={1} max={20} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" isLoading={updateEvent.isPending}>
          {t('common.save')}
        </Button>
      </form>
    </Form>
  )
}
