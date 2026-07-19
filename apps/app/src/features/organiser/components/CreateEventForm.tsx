import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import type { OrgEvent, Venue } from '../api'
import { useCreateEvent } from '../hooks/useCreateEvent'
import { useVenues } from '../hooks/useVenues'
import { CreateVenueForm } from './CreateVenueForm'
import { DateTimeInput } from './DateTimeInput'
import { EventImageUploader } from './EventImageUploader'

const schema = z
  .object({
    name: z.string().min(1),
    description: z.string().optional(),
    image_url: z.string().nullable().optional(),
    venue_id: z.string().min(1, 'Venue is required'),
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
  orgId: string
  onSuccess?: (eventId: string) => void
}

export function CreateEventForm({ orgId, onSuccess }: Props) {
  const { t } = useTranslation()
  const { data: venuesData } = useVenues()
  const venues = venuesData?.items ?? []
  const [venueModalOpen, setVenueModalOpen] = useState(false)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      description: '',
      image_url: null,
      venue_id: '',
      starts_at: '',
      ends_at: '',
      sale_starts_at: '',
      sale_ends_at: '',
      max_tickets_per_user: 4,
    },
  })

  const createEvent = useCreateEvent(orgId, (event: OrgEvent) => {
    form.reset()
    onSuccess?.(event.id)
  })

  return (
    <>
      <Dialog open={venueModalOpen} onClose={() => setVenueModalOpen(false)} title="New venue">
        <CreateVenueForm
          onSuccess={(venue: Venue) => {
            form.setValue('venue_id', venue.id, { shouldValidate: true })
            setVenueModalOpen(false)
          }}
        />
      </Dialog>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((v) =>
            createEvent.mutate({
              ...v,
              image_url: v.image_url ?? null,
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
          <FormField
            control={form.control}
            name="image_url"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Event image</FormLabel>
                <FormControl>
                  <EventImageUploader value={field.value ?? null} onChange={field.onChange} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="venue_id"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>{t('organiser.events.venueLabel')}</FormLabel>
                  <button
                    type="button"
                    onClick={() => setVenueModalOpen(true)}
                    className="text-primary flex items-center gap-1 text-xs font-medium"
                  >
                    <Plus className="h-3 w-3" />
                    New venue
                  </button>
                </div>
                <FormControl>
                  <select
                    className="border-input bg-background ring-offset-background focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                    {...field}
                  >
                    <option value="">
                      {venues.length === 0 ? 'No venues yet — create one' : 'Select a venue…'}
                    </option>
                    {venues.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} — {v.city}
                      </option>
                    ))}
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {(
            [
              ['starts_at', t('organiser.events.startsAtLabel')],
              ['ends_at', t('organiser.events.endsAtLabel')],
              ['sale_starts_at', t('organiser.events.saleStartsAtLabel')],
              ['sale_ends_at', t('organiser.events.saleEndsAtLabel')],
            ] as const
          ).map(([name, label]) => (
            <FormField
              key={name}
              control={form.control}
              name={name}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{label}</FormLabel>
                  <FormControl>
                    <DateTimeInput value={field.value} onChange={field.onChange} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          ))}
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
          <Button type="submit" isLoading={createEvent.isPending}>
            {t('organiser.events.create')}
          </Button>
        </form>
      </Form>
    </>
  )
}
