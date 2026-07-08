import { createFileRoute, Link, useNavigate, useSearch } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

import { Card, CardContent } from '@/components/ui/card'
import { useEvent } from '@/features/events/hooks/useEvent'
import type { Reservation } from '@/features/tickets/api'
import { CheckoutForm } from '@/features/tickets/components/CheckoutForm'

const searchSchema = z.object({
  reservation_window_token: z.string().optional(),
})

export const Route = createFileRoute('/_app/events/$eventId/checkout')({
  validateSearch: searchSchema,
  component: CheckoutPage,
})

function CheckoutPage() {
  const { t } = useTranslation()
  const { eventId } = Route.useParams()
  const { reservation_window_token } = useSearch({ from: '/_app/events/$eventId/checkout' })
  const navigate = useNavigate()
  const { data: event, isLoading, isError } = useEvent(eventId)

  const handleReservationCreated = (reservation: Reservation) => {
    void navigate({ to: '/reservations/$reservationId', params: { reservationId: reservation.id } })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  if (isError || !event) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <p className="text-muted-foreground">{t('events.notFound')}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-md space-y-6 p-6">
      <Link
        to="/events/$eventId"
        params={{ eventId }}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('events.backToEvent')}
      </Link>

      <div>
        <h1 className="text-2xl font-bold">{t('tickets.checkout.title')}</h1>
        <p className="text-muted-foreground text-sm">{event.name}</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <CheckoutForm
            eventId={eventId}
            ticketTypes={event.ticket_types}
            maxPerUser={event.max_tickets_per_user}
            reservationWindowToken={reservation_window_token}
            onSuccess={handleReservationCreated}
          />
        </CardContent>
      </Card>
    </div>
  )
}
