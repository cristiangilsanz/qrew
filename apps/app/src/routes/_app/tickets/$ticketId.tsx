import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  Calendar,
  ChevronDown,
  Clock,
  CreditCard,
  Info,
  MapPin,
  ShieldCheck,
  ShieldX,
  ShoppingBag,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { Dialog } from '@/components/ui/dialog'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { TicketDetailSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketListing } from '@/features/market/hooks/useMarketListing'
import { QrDisplay } from '@/features/tickets/components/QrDisplay'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { useReservation } from '@/features/tickets/hooks/useReservation'
import { useTicket } from '@/features/tickets/hooks/useTicket'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/tickets/$ticketId')({
  component: TicketDetailPage,
})


function fmt(iso: string) {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function TicketDetailPage() {
  const { ticketId } = Route.useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [timelineOpen, setTimelineOpen] = useState(false)
  const [saleConfirmOpen, setSaleConfirmOpen] = useState(false)
  const [saleCountdown, setSaleCountdown] = useState(5)

  useEffect(() => {
    if (!saleConfirmOpen) { setSaleCountdown(5); return }
    if (saleCountdown <= 0) return
    const timer = setTimeout(() => setSaleCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [saleConfirmOpen, saleCountdown])
  const { data: ticket, isLoading, isError } = useTicket(ticketId)
  const { data: event } = useEvent(ticket?.event_id ?? '')
  const { data: reservation } = useReservation(
    ticket?.reservation_id ?? '',
    ticket?.state === 'reserved',
  )
  const countdown = useCountdown(reservation?.expires_at)
  const isExpired =
    ticket?.state === 'expired' ||
    reservation?.status === 'expired'

  const saleEnded =
    event?.availability_status === 'ended' || event?.availability_status === 'sold_out'
  const eventStartsSoon =
    event?.starts_at != null &&
    new Date(event.starts_at).getTime() - Date.now() < 24 * 60 * 60 * 1000
  const canListForResale = ticket?.state === 'issued' && saleEnded && !eventStartsSoon

  const { data: existingListing } = useMarketListing(ticketId, canListForResale)

  const listForResale = useMutation({
    mutationFn: () => marketApi.listTicket(ticketId),
    onSuccess: () => {
      toast.success('Ticket listed on the resale market')
      void queryClient.invalidateQueries({ queryKey: ['market', 'listing', ticketId] })
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
    },
    onError: () => toast.error('Could not list ticket for resale'),
  })

  if (isLoading) return <TicketDetailSkeleton />

  if (isError || !ticket) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">{t('tickets.ticket.notFound')}</p>
        <Link to="/tickets" className="text-primary mt-4 inline-block text-sm underline">
          {t('tickets.backToTickets')}
        </Link>
      </div>
    )
  }

  const imageUrl = getEventImageUrl(event?.image_url)
  const startDate = event?.starts_at ? new Date(event.starts_at) : null
  const ticketType = event?.ticket_types.find((tt) => tt.id === ticket.ticket_type_id)

  // Build timeline
  type TLStatus = 'done' | 'pending' | 'error'
  interface TLItem {
    label: string
    date: string | null
    status: TLStatus
  }
  const timeline: TLItem[] = []

  timeline.push({ label: 'Reserved', date: fmt(ticket.created_at), status: 'done' })

  if (ticket.state === 'expired') {
    timeline.push({
      label: 'Expired',
      date: ticket.expired_at ? fmt(ticket.expired_at) : null,
      status: 'error',
    })
  } else if (ticket.state === 'cancelled') {
    if (ticket.issued_at) {
      timeline.push({ label: 'Issued', date: fmt(ticket.issued_at), status: 'done' })
    }
    timeline.push({
      label: 'Cancelled',
      date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
      status: 'error',
    })
  } else if (ticket.state === 'reserved') {
    // still pending issuance — no placeholder shown
  } else {
    // issued, entry_pending, used, frozen, flagged
    timeline.push({
      label: 'Issued',
      date: ticket.issued_at ? fmt(ticket.issued_at) : null,
      status: 'done',
    })
    if (ticket.state === 'entry_pending') {
      timeline.push({ label: 'Scanned', date: null, status: 'pending' })
    } else if (ticket.state === 'used') {
      timeline.push({
        label: 'Used',
        date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
        status: 'done',
      })
    } else if (ticket.state === 'frozen') {
      timeline.push({
        label: 'Frozen',
        date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
        status: 'error',
      })
    } else if (ticket.state === 'flagged') {
      timeline.push({
        label: 'Flagged',
        date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
        status: 'error',
      })
    }
  }

  return (
    <div className="min-h-screen px-4 pt-2 pb-24">
      <BackButton to="/tickets" className="mb-3" />

      <div className="mx-auto max-w-sm rounded-[2.5rem] bg-neutral-800 p-5">
        <div className="overflow-hidden rounded-3xl bg-white shadow-2xl">
          {/* Event image with name + venue overlaid at bottom center */}
          <div className="relative h-64 overflow-hidden rounded-t-3xl bg-black">
            <ImageWithSkeleton
              src={imageUrl}
              alt={event?.name}
              className={cn(
                'h-full w-full translate-y-5',
                event?.image_url ? 'object-cover opacity-85' : 'object-contain p-6 opacity-60',
              )}
              skeletonClassName="bg-neutral-700"
            />
            <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black to-transparent" />
            <div className="absolute top-0 right-0 left-0 px-4 pt-3 text-center text-white">
              <p className="text-sm leading-tight font-bold drop-shadow">{event?.name ?? '—'}</p>
              {event?.venue && (
                <p className="mt-0.5 flex items-center justify-center gap-1 text-xs text-white/70">
                  <MapPin className="h-3 w-3 shrink-0" />
                  {event.venue.name}, {event.venue.city}
                </p>
              )}
            </div>
          </div>

          {/* Holder strip */}
          {(ticket.holder_name || ticket.holder_dni) && (
            <div className="px-5 pt-4 pb-3 text-center">
              {ticket.holder_name && (
                <p className="text-base font-bold text-gray-800">{ticket.holder_name}</p>
              )}
              {ticket.holder_dni && (
                <p className="mt-0.5 font-mono text-xs text-gray-400">{ticket.holder_dni}</p>
              )}
            </div>
          )}

          {/* ID strip */}
          <div className="bg-gray-50 px-5 py-3">
            {ticketType && (
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs tracking-wide text-gray-400 uppercase">Ticket type</p>
                <p className="text-sm font-semibold text-gray-700">{ticketType.name}</p>
              </div>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs tracking-wide text-gray-400 uppercase">Ticket ID</p>
              <p className="font-mono text-sm font-semibold tracking-widest text-gray-700">
                {ticket.id.slice(0, 8).toUpperCase()}
              </p>
            </div>
          </div>

          {/* Info grid — Date + Time */}
          <div className="grid grid-cols-2 gap-px border-t border-gray-100">
            <div className="flex flex-col items-center gap-1 px-4 py-4">
              <Calendar className="h-4 w-4 text-gray-400" />
              <p className="text-xs tracking-wide text-gray-400 uppercase">Date</p>
              <p className="text-center text-sm font-semibold text-gray-900">
                {startDate
                  ? startDate.toLocaleDateString('en-GB', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })
                  : '—'}
              </p>
            </div>
            <div className="flex flex-col items-center gap-1 border-l border-gray-100 px-4 py-4">
              <Clock className="h-4 w-4 text-gray-400" />
              <p className="text-xs tracking-wide text-gray-400 uppercase">Time</p>
              <p className="text-center text-sm font-semibold text-gray-900">
                {startDate
                  ? startDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
                  : '—'}
              </p>
            </div>
          </div>

          {/* Timeline toggle */}
          <button
            onClick={() => setTimelineOpen((o) => !o)}
            className="flex w-full items-center justify-between border-t border-gray-100 bg-gray-50 px-5 py-3"
          >
            <p className="text-xs font-semibold tracking-wide text-gray-400 uppercase">History</p>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-gray-400 transition-transform',
                timelineOpen && 'rotate-180',
              )}
            />
          </button>

          {timelineOpen && (
            <div className="bg-gray-50 px-6 pt-1 pb-4">
              <ol className="space-y-0">
                {timeline.map((item, i) => (
                  <li key={i} className="flex gap-3">
                    {/* Dot + line */}
                    <div className="flex flex-col items-center">
                      <div
                        className={cn(
                          'mt-1 h-2.5 w-2.5 shrink-0 rounded-full',
                          item.status === 'done' && 'bg-green-500',
                          item.status === 'pending' && 'border-2 border-gray-300 bg-white',
                          item.status === 'error' && 'bg-red-400',
                        )}
                      />
                      {i < timeline.length - 1 && (
                        <div
                          className="my-0.5 w-px flex-1 bg-gray-200"
                          style={{ minHeight: '20px' }}
                        />
                      )}
                    </div>
                    {/* Text */}
                    <div className="pb-3">
                      <p
                        className={cn(
                          'text-sm leading-none font-semibold',
                          item.status === 'done' && 'text-gray-800',
                          item.status === 'pending' && 'text-gray-400',
                          item.status === 'error' && 'text-red-500',
                        )}
                      >
                        {item.label}
                      </p>
                      {item.date && <p className="mt-0.5 text-xs text-gray-400">{item.date}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Perforation */}
          <div className="relative flex items-center border-t border-gray-100">
            <div className="h-5 w-5 shrink-0 -translate-x-1/2 rounded-full bg-neutral-800 shadow-inner" />
            <div className="flex-1 border-t-2 border-dashed border-gray-200" />
            <div className="h-5 w-5 shrink-0 translate-x-1/2 rounded-full bg-neutral-800 shadow-inner" />
          </div>

          {ticket.qr_eligible ? (
            <div className="px-5 py-5">
              <QrDisplay ticketId={ticket.id} />
              {saleEnded && ticket?.state === 'issued' && !existingListing && (
                <>
                  <button
                    onClick={() => !eventStartsSoon && setSaleConfirmOpen(true)}
                    disabled={listForResale.isPending || eventStartsSoon}
                    className={cn(
                      'mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 py-3 text-sm font-medium text-gray-500 transition-colors disabled:opacity-40',
                      !eventStartsSoon && 'hover:border-gray-300 hover:text-gray-700',
                    )}
                  >
                    {listForResale.isPending ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
                    ) : (
                      <ShoppingBag className="h-4 w-4" />
                    )}
                    Sale
                  </button>
                  <p className="mt-1.5 flex items-center gap-1 text-xs text-gray-400">
                    <Info className="h-3 w-3 shrink-0" />
                    Listing closes 24h before the event
                  </p>
                </>
              )}
              {existingListing && existingListing.state === 'available' && (
                <p className="mt-4 text-center text-xs text-gray-400">
                  Listed · waiting for a buyer
                </p>
              )}
            </div>
          ) : ticket.state === 'reserved' ? (
            <div className="flex h-[300px] flex-col items-center justify-center gap-3 px-5 text-center">
              {isExpired ? (
                <>
                  <ShieldX className="h-10 w-10 text-gray-400" />
                  <p className="text-sm font-semibold text-gray-600">Reservation expired</p>
                </>
              ) : (
                <>
                  <CreditCard className="h-10 w-10 text-yellow-500" />
                  <p className="text-sm font-semibold text-gray-600">Awaiting payment</p>
                </>
              )}
            </div>
          ) : (
            <div className="flex h-[300px] flex-col items-center justify-center gap-2 px-5 text-center">
              {ticket.state === 'used' ? (
                <ShieldCheck className="h-10 w-10 text-gray-400" />
              ) : ticket.state === 'frozen' ? (
                <ShoppingBag className="h-10 w-10 text-gray-400" />
              ) : (
                <ShieldX className="h-10 w-10 text-gray-400" />
              )}
              <p className="text-sm font-semibold text-gray-600">
                {ticket.state === 'used' && 'Already scanned'}
                {ticket.state === 'cancelled' && 'Ticket cancelled'}
                {ticket.state === 'expired' && 'Reservation expired'}
                {ticket.state === 'frozen' && 'Listed on Resale Market'}
                {ticket.state === 'flagged' && 'Under review'}
              </p>
              <p className="text-xs text-gray-400">
                {ticket.state === 'used' && 'This ticket has already been used for entry.'}
                {ticket.state === 'cancelled' && 'This ticket is no longer valid.'}
                {ticket.state === 'frozen' && 'This ticket has been frozen.'}
                {ticket.state === 'flagged' && 'This ticket has been flagged for review.'}
              </p>
              {(ticket.state === 'frozen' || ticket.state === 'flagged') && (
                <p className="text-xs text-gray-400">
                  Contact support if you believe this is an error.
                </p>
              )}
              {ticket.state === 'frozen' && (
                <p className="mt-8 text-xs text-gray-400">
                  If unsold, your ticket will be returned automatically.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
      <Dialog
        open={saleConfirmOpen}
        onClose={() => setSaleConfirmOpen(false)}
        title="List ticket for sale"
      >
        <div className="space-y-3 text-sm text-gray-600">
          <p>
            Your ticket will be <strong>frozen</strong> and listed on the resale market at the
            original price. No markup, no speculation.
          </p>
          <ul className="space-y-1 text-xs text-gray-500 list-disc pl-4">
            <li>The QR code will be disabled until the ticket is sold or returned</li>
            <li>If unsold before the event, it will be returned to you automatically</li>
            <li>You cannot undo this action yourself once listed</li>
          </ul>
        </div>
        <div className="mt-5 flex gap-3">
          <button
            onClick={() => setSaleConfirmOpen(false)}
            className="flex-1 rounded-xl border border-gray-200 py-2.5 text-sm font-medium text-gray-500 transition hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              listForResale.mutate()
              setSaleConfirmOpen(false)
            }}
            disabled={saleCountdown > 0 || listForResale.isPending}
            className="flex-1 rounded-xl bg-gray-900 py-2.5 text-sm font-semibold text-white transition disabled:opacity-40"
          >
            {saleCountdown > 0 ? `Confirm (${saleCountdown})` : 'Confirm'}
          </button>
        </div>
      </Dialog>
    </div>
  )
}
