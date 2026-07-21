import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, RefreshCw, Users } from 'lucide-react'
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

import type { OrgEvent, Venue } from '../api'
import { useUpdateEvent } from '../hooks/useUpdateEvent'
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
    queue_required: z.boolean(),
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

function toLocalIso(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toISOString().slice(0, 16)
}

interface Props {
  event: OrgEvent
  orgId: string
}


const frostedInput =
  'w-full rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2.5 text-sm text-white/50 outline-none transition-all duration-150 placeholder:text-white/20 focus:border-primary/50 focus:bg-white/8 focus:text-white'

export function EditEventForm({ event, orgId }: Props) {
  const { t } = useTranslation()
  const { data: venuesData } = useVenues()
  const venues = venuesData?.items ?? []
  const [venueModalOpen, setVenueModalOpen] = useState(false)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: event.name,
      description: event.description ?? '',
      image_url: event.image_url ?? null,
      venue_id: event.venue_id ?? '',
      starts_at: toLocalIso(event.starts_at),
      ends_at: toLocalIso(event.ends_at),
      sale_starts_at: toLocalIso(event.sale_starts_at),
      sale_ends_at: toLocalIso(event.sale_ends_at),
      max_tickets_per_user: event.max_tickets_per_user,
      queue_required: event.queue_required,
    },
  })

  const updateEvent = useUpdateEvent(orgId, event.id)

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
            updateEvent.mutate({
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
                  <input className={frostedInput} {...field} />
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
                  <textarea rows={3} className={`${frostedInput} resize-none`} {...field} />
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
                  <select className={`${frostedInput} [&>option]:bg-[hsl(0,0%,12%)]`} {...field}>
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
                  <input type="number" min={1} max={20} className={frostedInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="queue_required"
            render={({ field }) => (
              <FormItem>
                <button
                  type="button"
                  onClick={() => field.onChange(!field.value)}
                  className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all duration-150 ${
                    field.value
                      ? 'border-primary/40 bg-primary/10 text-white'
                      : 'border-white/8 bg-white/[0.03] text-white/50'
                  }`}
                >
                  <Users className={`h-4 w-4 shrink-0 ${field.value ? 'text-primary' : ''}`} />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Enable queue</p>
                    <p className={`text-xs ${field.value ? 'text-white/60' : 'text-white/30'}`}>
                      Attendees join a virtual queue before entry
                    </p>
                  </div>
                  <div
                    className={`h-5 w-9 rounded-full transition-colors ${field.value ? 'bg-primary' : 'bg-white/20'}`}
                  >
                    <div
                      className={`m-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${field.value ? 'translate-x-4' : 'translate-x-0'}`}
                    />
                  </div>
                </button>
              </FormItem>
            )}
          />
          <div className="flex justify-end">
            <Button type="submit" isLoading={updateEvent.isPending} className="rounded-full px-6">
              <RefreshCw className="h-4 w-4" />
              {t('organiser.events.updateEvent')}
            </Button>
          </div>
        </form>
      </Form>
    </>
  )
}
