import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { TicketState } from '@/features/tickets/api'
import { QrDisplay } from '@/features/tickets/components/QrDisplay'
import { useTicket } from '@/features/tickets/hooks/useTicket'

export const Route = createFileRoute('/_app/tickets/$ticketId')({
  component: TicketDetailPage,
})

const STATE_VARIANT: Record<TicketState, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  reserved: 'secondary',
  issued: 'default',
  entry_pending: 'default',
  used: 'outline',
  cancelled: 'destructive',
  frozen: 'destructive',
  flagged: 'destructive',
}

const QR_ELIGIBLE: TicketState[] = ['issued', 'entry_pending']

function TicketDetailPage() {
  const { ticketId } = Route.useParams()
  const { t } = useTranslation()
  const { data: ticket, isLoading, isError } = useTicket(ticketId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  if (isError || !ticket) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-center">
        <p className="text-muted-foreground">{t('tickets.ticket.notFound')}</p>
        <Link to="/tickets" className="text-primary mt-4 inline-block text-sm underline">
          {t('tickets.backToTickets')}
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg space-y-6 p-6">
      <Link
        to="/tickets"
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('tickets.backToTickets')}
      </Link>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{t('tickets.ticket.title')}</CardTitle>
            <Badge variant={STATE_VARIANT[ticket.state]}>
              {t(`tickets.ticket.states.${ticket.state}`)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('tickets.ticket.idLabel')}</span>
            <span className="font-mono text-xs">{ticket.id.slice(0, 8).toUpperCase()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">{t('tickets.ticket.issuedLabel')}</span>
            <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
          </div>
          {ticket.state === 'frozen' && (
            <p className="text-destructive mt-2 text-xs">{t('tickets.ticket.frozenHint')}</p>
          )}
          {ticket.state === 'flagged' && (
            <p className="text-destructive mt-2 text-xs">{t('tickets.ticket.flaggedHint')}</p>
          )}
        </CardContent>
      </Card>

      {QR_ELIGIBLE.includes(ticket.state) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('tickets.qr.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <QrDisplay ticketId={ticket.id} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
