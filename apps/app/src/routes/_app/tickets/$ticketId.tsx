import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowLeftRight,
  Calendar,
  ChevronDown,
  Clock,
  CreditCard,
  Flag,
  Info,
  MapPin,
  ScanLine,
  ShieldCheck,
  ShieldX,
  ShoppingBag,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { TicketDetailSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketListing } from '@/features/market/hooks/useMarketListing'
import { useProfile } from '@/features/profile/hooks/useProfile'
import { QrDisplay } from '@/features/tickets/components/QrDisplay'
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
  const { data: profile } = useProfile()
  const { data: ticket, isLoading: ticketLoading, isError } = useTicket(ticketId)
  const { data: event, isLoading: eventLoading } = useEvent(ticket?.event_id ?? '')
  const { data: reservation } = useReservation(
    ticket?.reservation_id ?? '',
    ticket?.state === 'reserved',
  )
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
      toast.success(t('tickets.toast.listSuccess'))
      void queryClient.invalidateQueries({ queryKey: ['market', 'listing', ticketId] })
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      setTimeout(() => window.location.reload(), 300)
    },
    onError: () => toast.error(t('tickets.toast.listFailed')),
  })

  const isLoading = ticketLoading || (!!ticket && eventLoading)
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

  timeline.push({ label: t('tickets.ticket.timeline.reserved'), date: fmt(ticket.created_at), status: 'done' })

  if (ticket.state === 'expired') {
    timeline.push({
      label: t('tickets.ticket.timeline.expired'),
      date: ticket.expired_at ? fmt(ticket.expired_at) : null,
      status: 'error',
    })
  } else if (ticket.state === 'cancelled') {
    if (ticket.issued_at) {
      timeline.push({ label: t('tickets.ticket.timeline.issued'), date: fmt(ticket.issued_at), status: 'done' })
    }
    timeline.push({
      label: t('tickets.ticket.timeline.cancelled'),
      date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
      status: 'error',
    })
  } else if (ticket.state === 'reserved') {
    // still pending issuance — no placeholder shown
  } else {
    // issued, scanning, redeemed, on_sale, flagged
    timeline.push({
      label: t('tickets.ticket.timeline.issued'),
      date: ticket.issued_at ? fmt(ticket.issued_at) : null,
      status: 'done',
    })
    if (ticket.state === 'scanning') {
      timeline.push({ label: t('tickets.ticket.timeline.scanned'), date: null, status: 'pending' })
    } else if (ticket.state === 'redeemed') {
      timeline.push({
        label: t('tickets.ticket.timeline.redeemed'),
        date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
        status: 'done',
      })
    } else if (ticket.state === 'on_sale') {
      timeline.push({
        label: t('tickets.ticket.timeline.onSale'),
        date: ticket.state_updated_at ? fmt(ticket.state_updated_at) : null,
        status: 'error',
      })
    } else if (ticket.state === 'flagged') {
      timeline.push({
        label: t('tickets.ticket.timeline.flagged'),
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
          {(ticket.holder_name || ticket.holder_dni || ticket.state === 'expired') && (
            <div className="px-5 pt-4 pb-3 text-center">
              <p className="text-base font-bold text-gray-800">
                {ticket.holder_name ?? profile?.full_name ?? ''}
              </p>
              {ticket.holder_dni && (
                <p className="mt-0.5 font-mono text-xs text-gray-400">{ticket.holder_dni}</p>
              )}
            </div>
          )}

          {/* ID strip */}
          <div className="bg-white px-5 pt-3 pb-5">
            {ticketType && (
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs tracking-wide text-gray-400 uppercase">{t('tickets.ticket.typeLabel')}</p>
                <p className="text-sm font-semibold text-gray-700">{ticketType.name}</p>
              </div>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs tracking-wide text-gray-400 uppercase">{t('tickets.ticket.idShortLabel')}</p>
              <p className="font-mono text-sm font-semibold tracking-widest text-gray-700">
                {ticket.id.slice(0, 8).toUpperCase()}
              </p>
            </div>
          </div>

          {/* Info grid — Date + Time */}
          <div className="grid grid-cols-2 gap-px">
            <div className="flex flex-col items-center gap-1 px-4 py-4">
              <Calendar className="h-4 w-4 text-gray-400" />
              <p className="text-xs tracking-wide text-gray-400 uppercase">{t('tickets.ticket.dateLabel')}</p>
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
            <div className="flex flex-col items-center gap-1 px-4 py-4">
              <Clock className="h-4 w-4 text-gray-400" />
              <p className="text-xs tracking-wide text-gray-400 uppercase">{t('tickets.ticket.timeLabel')}</p>
              <p className="text-center text-sm font-semibold text-gray-900">
                {startDate
                  ? startDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
                  : '—'}
              </p>
            </div>
          </div>

          {/* History — separate rounded expandable */}
          <div className="mx-4 mt-4 mb-5 overflow-hidden rounded-2xl border border-gray-100">
            <button
              onClick={() => setTimelineOpen((o) => !o)}
              className="flex w-full items-center justify-between bg-gray-50 px-4 py-3"
            >
              <p className="text-xs font-semibold tracking-wide text-gray-400 uppercase">{t('tickets.ticket.historyLabel')}</p>
              <ChevronDown
                className={cn(
                  'h-4 w-4 text-gray-400 transition-transform',
                  timelineOpen && 'rotate-180',
                )}
              />
            </button>

            {timelineOpen && (
              <div className="bg-white px-5 pt-3 pb-4">
                <ol className="space-y-0">
                  {timeline.map((item, i) => (
                    <li key={i} className="flex gap-3">
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
          </div>

          {/* Perforation */}
          <div className="relative mt-4 flex items-center">
            <div className="h-5 w-5 shrink-0 -translate-x-1/2 rounded-full bg-neutral-800 shadow-inner" />
            <div className="flex-1 border-t-2 border-dashed border-gray-200" />
            <div className="h-5 w-5 shrink-0 translate-x-1/2 rounded-full bg-neutral-800 shadow-inner" />
          </div>

          {ticket.qr_eligible && ticket.state !== 'scanning' ? (
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
                    {t('tickets.ticket.sale.button')}
                  </button>
                  <p className="mt-1.5 flex items-center gap-1 text-xs text-gray-400">
                    <Info className="h-3 w-3 shrink-0" />
                    {t('tickets.ticket.sale.closes')}
                  </p>
                </>
              )}
            </div>
          ) : ticket.state === 'reserved' ? (
            <div className="flex h-[300px] flex-col items-center justify-center gap-3 px-5 text-center">
              {isExpired ? (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <Clock className="h-6 w-6 text-gray-400" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.paymentExpired')}</p>
                </>
              ) : (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <CreditCard className="h-6 w-6 text-yellow-500" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.paymentPending')}</p>
                </>
              )}
            </div>
          ) : (
            <div className="flex h-[300px] flex-col items-center justify-center gap-3 px-5 text-center">
              {ticket.state === 'redeemed' && (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <ShieldCheck className="h-6 w-6 text-green-500" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.redeemed')}</p>
                </>
              )}
              {ticket.state === 'scanning' && (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <ScanLine className="h-6 w-6 text-purple-400" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.scanning')}</p>
                </>
              )}
              {ticket.state === 'cancelled' && (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <ShieldX className="h-6 w-6 text-red-400" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.cancelled')}</p>
                </>
              )}
              {ticket.state === 'expired' && (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <Clock className="h-6 w-6 text-gray-400" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.paymentExpired')}</p>
                </>
              )}
              {ticket.state === 'on_sale' && (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <ShoppingBag className="h-6 w-6 text-blue-400" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.onSale')}</p>
                </>
              )}
              {ticket.state === 'flagged' && (
                <>
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                    <Flag className="h-6 w-6 text-amber-900" />
                  </div>
                  <p className="text-xs text-gray-400">{t('tickets.ticket.status.flagged')}</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>
      <AnimatePresence>
        {saleConfirmOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setSaleConfirmOpen(false)}
          >
            <motion.div
              initial={{ y: 32, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 32, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-orange-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-orange-500/10">
                  <ArrowLeftRight className="h-5 w-5 text-orange-400" />
                </div>
                <h3 className="text-base font-semibold text-orange-400">{t('tickets.ticket.sale.title')}</h3>
              </div>

              <p className="text-muted-foreground mb-4 text-sm">
                {t('tickets.ticket.sale.description')}
              </p>

              <div className="text-muted-foreground mb-6 flex gap-1.5 text-xs">
                <Info className="mt-0.5 h-3 w-3 shrink-0" />
                <p>{t('tickets.ticket.sale.note')}</p>
              </div>

              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setSaleConfirmOpen(false)}
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={() => {
                    listForResale.mutate()
                    setSaleConfirmOpen(false)
                  }}
                  disabled={saleCountdown > 0 || listForResale.isPending}
                  className="flex h-10 min-w-[120px] items-center justify-center gap-2 rounded-full bg-yellow-400 px-5 text-sm font-semibold text-black disabled:opacity-40"
                >
                  <ArrowLeftRight className="h-3.5 w-3.5" />
                  {saleCountdown > 0 ? t('common.waitSeconds', { seconds: saleCountdown }) : t('tickets.ticket.sale.confirm')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
