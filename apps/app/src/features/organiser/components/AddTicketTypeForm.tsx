// renders the add ticket type form component
import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
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

import { useCreateTicketType } from '../hooks/useCreateTicketType'

const createSchema = z.object({
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
  currency: z.literal('EUR').default('EUR'),
  position: z.coerce.number().int().optional(),
})

type CreateValues = z.infer<typeof createSchema>

const darkInput =
  'border-white/15 bg-white/5 text-white placeholder:text-white/30 focus:border-primary/60 w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-colors'

interface Props {
  eventId: string
  onClose: () => void
}

// renders the add ticket type form component
export function AddTicketTypeForm({ eventId, onClose }: Props) {
  const { t } = useTranslation()
  const createTt = useCreateTicketType(eventId)
  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: '', description: '', capacity: 100, price_cents: 0 },
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          createTt.mutate(v)
          form.reset()
          onClose()
        })}
        className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5"
      >
        <p className="text-sm font-semibold">{t('organiser.ticketTypes.addButton')}</p>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.nameLabel')}</FormLabel>
              <FormControl>
                <input className={darkInput} placeholder="General Admission" {...field} />
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
                    className={darkInput}
                    placeholder="0.00"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="flex justify-between pt-1">
          <button
            type="button"
            className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <Button type="submit" isLoading={createTt.isPending} className="rounded-full px-6">
            <Plus className="h-4 w-4" />
            {t('organiser.ticketTypes.addButton')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
