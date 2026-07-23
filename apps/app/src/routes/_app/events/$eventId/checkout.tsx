import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router'
import axios from 'axios'
import { Minus, Plus, Ticket } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'

import { BackButton } from '@/components/ui/back-button'
import { CheckoutSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { ticketsApi } from '@/features/tickets/api'
import { useTickets } from '@/features/tickets/hooks/useTickets'
import { cn } from '@/lib/utils'

const searchSchema = z.object({
  reservation_window_token: z.string().optional(),
  admitted: z.boolean().optional(),
})

export const Route = createFileRoute('/_app/events/$eventId/checkout')({
  validateSearch: searchSchema,
  component: CheckoutPage,
})

function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

function CheckoutPage() {
  const { t } = useTranslation()
  const { eventId } = Route.useParams()
  const { reservation_window_token, admitted } = useSearch({ from: '/_app/events/$eventId/checkout' })
  const navigate = useNavigate()

  const { data: event, isLoading: eventLoading, isError } = useEvent(eventId)
  const { data: myTickets, isLoading: ticketsLoading } = useTickets()

  const [quantities, setQuantities] = useState<Record<string, number>>({})
  const [isPending, setIsPending] = useState(false)

  const isLoading = eventLoading || ticketsLoading
  if (isLoading) return <CheckoutSkeleton />

  if (isError || !event) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">{t('events.notFound')}</p>
      </div>
    )
  }

  // Queue flow — show join button unless user was admitted from the queue
  if (event.queue_required && !admitted) {
    return (
      <div className="mx-auto max-w-[430px] space-y-6 px-4 pt-5 pb-28">
        <BackButton
          onClick={() => void navigate({ to: '/events/$eventId', params: { eventId } })}
        />
        <div className="fixed inset-x-0 bottom-24 z-40">
          <div className="mx-auto max-w-[430px] bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent px-4 pt-3 pb-6">
            <button
              className="bg-primary text-primary-foreground hover:bg-primary/90 h-12 w-full rounded-full text-sm font-semibold"
              onClick={() => void navigate({ to: '/events/$eventId/queue', params: { eventId } })}
            >
              {t('tickets.queue.joinButton')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  const ticketTypes = event.ticket_types.slice().sort((a, b) => a.position - b.position)
  const totalSelected = Object.values(quantities).reduce((sum, q) => sum + q, 0)
  const alreadyHeld = myTickets?.filter(
    (t) => t.event_id === eventId && t.counts_toward_limit,
  ).length ?? 0
  const maxTotal = Math.max(0, event.max_tickets_per_user - alreadyHeld)

  const handleIncrement = (id: string, available: number) => {
    if (available === 0) return
    const current = quantities[id] ?? 0
    if (totalSelected >= maxTotal) return
    if (current >= available) return
    setQuantities((prev) => ({ ...prev, [id]: current + 1 }))
  }

  const handleDecrement = (id: string) => {
    const current = quantities[id] ?? 0
    if (current <= 0) return
    setQuantities((prev) => {
      const next = { ...prev }
      if (current === 1) {
        delete next[id]
      } else {
        next[id] = current - 1
      }
      return next
    })
  }

  const totalCents = ticketTypes.reduce((sum, tt) => {
    return sum + tt.price_cents * (quantities[tt.id] ?? 0)
  }, 0)

  const selectedTypes = ticketTypes.filter((tt) => (quantities[tt.id] ?? 0) > 0)
  const currency = selectedTypes[0]?.currency ?? 'EUR'
  const canReserve = totalSelected > 0 && !isPending

  const handleReserve = async () => {
    if (!canReserve) return
    setIsPending(true)
    try {
      let firstReservationId: string | null = null
      for (const tt of selectedTypes) {
        const reservation = await ticketsApi.createReservation(eventId, {
          ticket_type_id: tt.id,
          quantity: quantities[tt.id]!,
          reservation_window_token,
        })
        if (firstReservationId === null) firstReservationId = reservation.id
      }
      if (firstReservationId) {
        void navigate({
          to: '/reservations/$reservationId',
          params: { reservationId: firstReservationId },
        })
      } else {
        void navigate({ to: '/tickets' })
      }
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined
      const message =
        typeof detail === 'object' && detail?.message
          ? detail.message
          : typeof detail === 'string'
            ? detail
            : t('tickets.reservation.createFailed')
      console.error('[checkout] reservation failed', err)
      toast.error(message)
    } finally {
      setIsPending(false)
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-[430px] space-y-6 px-4 pt-5 pb-28">
      {/* Header */}
      <div>
        <BackButton
          onClick={() => void navigate({ to: '/events/$eventId', params: { eventId } })}
          className="mb-4"
        />
        <h1 className="text-xl font-bold">{event.name}</h1>
        <p className="text-muted-foreground text-sm">{event.organisation.name}</p>
      </div>

      {/* Ticket type cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">{t('events.ticketTypes')}</h2>
          <span className="text-muted-foreground text-xs">
            {totalSelected}/{maxTotal} {t('tickets.checkout.selected')}
            {alreadyHeld > 0 && (
              <span className="text-muted-foreground ml-1">
                ({alreadyHeld} {t('tickets.checkout.alreadyHeld')})
              </span>
            )}
          </span>
        </div>
        {maxTotal === 0 && (
          <p className="text-muted-foreground text-sm">
            {t('tickets.checkout.limitReached')}
          </p>
        )}

        {ticketTypes.map((tt) => {
          const qty = quantities[tt.id] ?? 0
          const isSelected = qty > 0
          const atTypeMax = qty >= Math.min(maxTotal, tt.available)
          const atTotalMax = totalSelected >= maxTotal

          return (
            <div
              key={tt.id}
              className={cn(
                'rounded-xl border p-4 transition-colors',
                tt.available === 0
                  ? 'border-border opacity-50'
                  : isSelected
                    ? 'border-primary bg-primary/10'
                    : 'border-border',
              )}
            >
              <div className="flex items-center gap-3">
                {/* Info */}
                <div className="min-w-0 flex-1">
                  <p className="leading-tight font-semibold">{tt.name}</p>
                  {tt.description && (
                    <p className="text-muted-foreground mt-0.5 text-xs">{tt.description}</p>
                  )}
                  {tt.available === 0 ? (
                    <span className="text-destructive mt-1 inline-block text-xs font-medium">
                      {t('events.soldOut')}
                    </span>
                  ) : (
                    <p className="text-primary mt-0.5 text-sm font-bold">
                      {formatPrice(tt.price_cents, tt.currency)}
                    </p>
                  )}
                </div>

                {/* Stepper */}
                {tt.available > 0 && (
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleDecrement(tt.id)}
                      disabled={qty === 0}
                      className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-full border transition-colors disabled:opacity-30',
                        isSelected ? 'border-primary text-primary' : 'border-border',
                      )}
                    >
                      <Minus className="h-3.5 w-3.5" />
                    </button>
                    <span
                      className={cn(
                        'w-5 text-center text-sm font-bold tabular-nums',
                        qty === 0 ? 'text-muted-foreground' : 'text-foreground',
                      )}
                    >
                      {qty}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleIncrement(tt.id, tt.available)}
                      disabled={atTypeMax || atTotalMax}
                      className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-full transition-colors disabled:opacity-30',
                        isSelected && qty > 0 ? 'bg-primary text-white' : 'border-border border',
                      )}
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Bottom bar */}
      <div className="fixed inset-x-0 bottom-24 z-40">
        <div className="mx-auto max-w-[430px] space-y-3 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent px-4 pt-8 pb-0">
          {totalSelected > 0 && (
            <div className="border-border flex items-center justify-between border-t pt-3 pb-1">
              <span className="text-muted-foreground text-sm">{t('tickets.checkout.total')}</span>
              <span className="text-lg font-bold">
                {totalCents === 0 ? 'Free' : formatPrice(totalCents, currency)}
              </span>
            </div>
          )}
          <button
            disabled={!canReserve}
            onClick={() => void handleReserve()}
            className="bg-primary hover:bg-primary/90 ml-auto flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors disabled:opacity-40"
          >
            {isPending ? (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <Ticket className="h-5 w-5 shrink-0" />
            )}
            <span className="text-sm font-semibold">{t('tickets.checkout.reserveButton')}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
