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
import type { TicketType } from '@/features/events/api'

import type { Reservation } from '../api'
import { useCreateReservation } from '../hooks/useCreateReservation'

const schema = z.object({
  ticket_type_id: z.string().min(1),
  quantity: z.coerce.number().int().min(1).max(20),
})

type Values = z.infer<typeof schema>

interface Props {
  eventId: string
  ticketTypes: TicketType[]
  maxPerUser: number
  reservationWindowToken?: string
  onSuccess: (reservation: Reservation) => void
}

function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${(cents / 100).toFixed(2)} ${currency}`
}

export function CheckoutForm({
  eventId,
  ticketTypes,
  maxPerUser,
  reservationWindowToken,
  onSuccess,
}: Props) {
  const { t } = useTranslation()
  const available = ticketTypes.filter((tt) => tt.available > 0)

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { ticket_type_id: available[0]?.id ?? '', quantity: 1 },
  })

  const createReservation = useCreateReservation(eventId, onSuccess)

  const selectedId = form.watch('ticket_type_id')
  const selectedTt = ticketTypes.find((tt) => tt.id === selectedId)
  const maxQty = Math.min(maxPerUser, selectedTt?.available ?? 1)

  if (available.length === 0) {
    return <p className="text-muted-foreground py-4 text-center text-sm">{t('events.soldOut')}</p>
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) =>
          createReservation.mutate({
            ...v,
            reservation_window_token: reservationWindowToken,
          }),
        )}
        className="space-y-4"
      >
        <FormField
          control={form.control}
          name="ticket_type_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tickets.checkout.ticketTypeLabel')}</FormLabel>
              <FormControl>
                <select
                  className="border-input bg-background ring-offset-background focus:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-offset-2 focus:outline-none"
                  {...field}
                >
                  {ticketTypes.map((tt) => (
                    <option key={tt.id} value={tt.id} disabled={tt.available === 0}>
                      {tt.name} — {formatPrice(tt.price_cents, tt.currency)}
                      {tt.available === 0 ? ` (${t('events.soldOut')})` : ''}
                    </option>
                  ))}
                </select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="quantity"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tickets.checkout.quantityLabel')}</FormLabel>
              <FormControl>
                <select
                  className="border-input bg-background ring-offset-background focus:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-offset-2 focus:outline-none"
                  {...field}
                >
                  {Array.from({ length: maxQty }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {selectedTt && (
          <p className="text-muted-foreground text-sm">
            {t('tickets.checkout.total')}:{' '}
            <span className="text-foreground font-semibold">
              {formatPrice(selectedTt.price_cents * form.watch('quantity'), selectedTt.currency)}
            </span>
          </p>
        )}
        <Button type="submit" className="w-full" isLoading={createReservation.isPending}>
          {t('tickets.checkout.reserveButton')}
        </Button>
      </form>
    </Form>
  )
}
