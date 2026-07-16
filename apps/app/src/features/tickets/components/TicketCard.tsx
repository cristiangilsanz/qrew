import { Link } from '@tanstack/react-router'
import { Ticket } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

import type { Ticket as TicketType, TicketState } from '../api'

const STATE_VARIANT: Record<TicketState, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  reserved: 'secondary',
  issued: 'default',
  entry_pending: 'default',
  used: 'outline',
  cancelled: 'destructive',
  frozen: 'destructive',
  flagged: 'destructive',
}

interface Props {
  ticket: TicketType
}

export function TicketCard({ ticket }: Props) {
  const { t } = useTranslation()

  return (
    <Link to="/tickets/$ticketId" params={{ ticketId: ticket.id }}>
      <Card className="hover:bg-muted/50 transition-colors">
        <CardContent className="flex items-center gap-4 p-4">
          <div className="bg-primary/10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
            <Ticket className="text-primary h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {t('tickets.ticket.id', { id: ticket.id.slice(0, 8) })}
            </p>
            <p className="text-muted-foreground text-xs">
              {new Date(ticket.created_at).toLocaleDateString()}
            </p>
          </div>
          <Badge variant={STATE_VARIANT[ticket.state]}>
            {t(`tickets.ticket.states.${ticket.state}`)}
          </Badge>
        </CardContent>
      </Card>
    </Link>
  )
}
