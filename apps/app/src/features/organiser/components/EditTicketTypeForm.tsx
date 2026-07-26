import { zodResolver } from '@hookform/resolvers/zod'
import { RefreshCw } from 'lucide-react'
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

import { useUpdateTicketType } from '../hooks/useUpdateTicketType'

const editSchema = z.object({
  name: z
    .string()
    .min(1)
    .max(32)
    .transform((v) => v.toLowerCase())
    .pipe(
      z
        .string()
        .regex(/^[a-z][a-z0-9_]{0,31}$/, 'Must start with a letter, no spaces or special chars'),
    ),
  description: z.string().optional(),
  capacity: z.coerce.number().int().min(1).max(100000),
  price_cents: z.coerce
    .number()
    .min(0)
    .max(100000)
    .transform((v) => Math.round(v * 100)),
  position: z.coerce.number().int().optional(),
})

const capacitySchema = z.object({
  capacity: z.coerce.number().int().min(1).max(100000),
})

export type EditTicketTypeValues = z.infer<typeof editSchema>
type CapacityValues = z.infer<typeof capacitySchema>

const darkInput =
  'border-white/15 bg-white/5 text-white placeholder:text-white/30 focus:border-primary/60 w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-colors'

interface EditProps {
  ttId: string
  eventId: string
  defaultValues: EditTicketTypeValues
  onClose: () => void
}

export function EditTicketTypeForm({ ttId, eventId, defaultValues, onClose }: EditProps) {
  const { t } = useTranslation()
  const updateTt = useUpdateTicketType(eventId)
  const form = useForm<EditTicketTypeValues>({
    resolver: zodResolver(editSchema),
    defaultValues,
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          updateTt.mutate({ ttId, data: v })
          onClose()
        })}
        className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5"
      >
        <p className="text-sm font-semibold">{t('organiser.ticketTypes.title')}</p>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.nameLabel')}</FormLabel>
              <FormControl>
                <input className={darkInput} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="capacity"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.ticketTypes.capacityLabel')}</FormLabel>
                <FormControl>
                  <input type="number" className={darkInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="price_cents"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.ticketTypes.priceLabel')} (€)</FormLabel>
                <FormControl>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    className={darkInput}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="position"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.positionLabel')}</FormLabel>
              <FormControl>
                <input type="number" className={darkInput} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-between pt-1">
          <button
            type="button"
            className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <Button type="submit" isLoading={updateTt.isPending} className="rounded-full px-6">
            <RefreshCw className="h-4 w-4" />
            {t('organiser.events.updateEvent')}
          </Button>
        </div>
      </form>
    </Form>
  )
}

interface CapacityEditProps {
  ttId: string
  eventId: string
  currentCapacity: number
  onClose: () => void
}

export function CapacityEditTicketTypeForm({
  ttId,
  eventId,
  currentCapacity,
  onClose,
}: CapacityEditProps) {
  const { t } = useTranslation()
  const updateTt = useUpdateTicketType(eventId)
  const form = useForm<CapacityValues>({
    resolver: zodResolver(capacitySchema),
    defaultValues: { capacity: currentCapacity },
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          updateTt.mutate({ ttId, data: { capacity: v.capacity } })
          onClose()
        })}
        className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5"
      >
        <FormField
          control={form.control}
          name="capacity"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.capacityLabel')}</FormLabel>
              <FormControl>
                <input type="number" className={darkInput} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-between pt-1">
          <button
            type="button"
            className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <Button type="submit" isLoading={updateTt.isPending} className="rounded-full px-6">
            <RefreshCw className="h-4 w-4" />
            {t('organiser.events.updateEvent')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
