import { createFileRoute, Link } from '@tanstack/react-router'
import { Ticket } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export const Route = createFileRoute('/_app/tickets/')({
  component: TicketsPage,
})

function TicketsPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-bold">{t('tickets.title')}</h1>

      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <Ticket className="text-muted-foreground h-12 w-12" />
        <p className="text-muted-foreground">{t('tickets.empty')}</p>
        <Link
          to="/events"
          className="text-primary hover:text-primary/80 text-sm underline underline-offset-4"
        >
          {t('tickets.browseEvents')}
        </Link>
      </div>
    </div>
  )
}
