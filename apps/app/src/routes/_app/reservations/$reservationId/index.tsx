import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ReservationSummary } from '@/features/tickets/components/ReservationSummary'
import { StripeCheckout } from '@/features/tickets/components/StripeCheckout'
import { useInitiatePayment } from '@/features/tickets/hooks/useInitiatePayment'
import { useReservation } from '@/features/tickets/hooks/useReservation'

export const Route = createFileRoute('/_app/reservations/$reservationId/')({
  component: ReservationPage,
})

function ReservationPage() {
  const { t } = useTranslation()
  const { reservationId } = Route.useParams()
  const navigate = useNavigate()
  const [clientSecret, setClientSecret] = useState<string | null>(null)

  const { data: reservation, isLoading, isError } = useReservation(reservationId, !!clientSecret)

  const initiatePayment = useInitiatePayment((payment) => {
    setClientSecret(payment.client_secret)
  })

  const handlePaySuccess = () => {
    toast.success(t('tickets.payment.success'))
    void navigate({ to: '/tickets' })
  }

  const handleCancel = () => {
    void navigate({ to: '/tickets' })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  if (isError || !reservation) {
    return (
      <div className="mx-auto max-w-md p-6">
        <p className="text-muted-foreground">{t('tickets.reservation.notFound')}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-md space-y-6 p-6">
      <Link
        to="/events"
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('events.backToList')}
      </Link>

      <h1 className="text-2xl font-bold">{t('tickets.reservation.title')}</h1>

      <ReservationSummary
        reservation={reservation}
        onCancel={handleCancel}
        onPay={() => initiatePayment.mutate(reservationId)}
        payLoading={initiatePayment.isPending}
      />

      {clientSecret && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('tickets.payment.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaySuccess} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
