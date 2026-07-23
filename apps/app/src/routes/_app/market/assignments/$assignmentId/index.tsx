import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import axios from 'axios'
import { Calendar, CheckCircle2, Clock, CreditCard, MapPin, ShieldX } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMarketAssignment } from '@/features/market/hooks/useMarketAssignment'
import { StripeCheckout } from '@/features/tickets/components/StripeCheckout'
import { useCountdown } from '@/features/tickets/hooks/useCountdown'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/assignments/$assignmentId/')({
  component: AssignmentPage,
})

function formatSeconds(s: number): string {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function formatPrice(cents: number, currency: string): string {
  if (cents === 0) return 'Free'
  return `${currency === 'EUR' ? '€' : currency}${(cents / 100).toFixed(2)}`
}

const validateDni = (dni: string): boolean => {
  const v = dni.trim().toUpperCase()
  const letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
  const dniRe = /^\d{8}[A-Z]$/
  const nieRe = /^[XYZ]\d{7}[A-Z]$/
  if (dniRe.test(v)) return letters[parseInt(v.slice(0, 8)) % 23] === v[8]
  if (nieRe.test(v)) {
    const prefix: Record<string, string> = { X: '0', Y: '1', Z: '2' }
    const digits = prefix[v[0]] + v.slice(1, 8)
    return letters[parseInt(digits) % 23] === v[8]
  }
  return false
}

function AssignmentPage() {
  const { assignmentId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: assignment, isLoading, isError } = useMarketAssignment(assignmentId)
  const { data: event } = useEvent(assignment?.event_id ?? '')
  const countdown = useCountdown(assignment?.state === 'pending' ? assignment.expires_at : null)

  const [holderName, setHolderName] = useState('')
  const [holderDni, setHolderDni] = useState('')
  const [clientSecret, setClientSecret] = useState<string | null>(null)

  const saveHolders = useMutation({
    mutationFn: () => marketApi.setHolders(assignmentId, holderName, holderDni),
    onError: (err) => {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined
      toast.error(
        typeof detail === 'object' && detail?.message
          ? detail.message
          : typeof detail === 'string'
            ? detail
            : 'Failed to save holder info',
      )
    },
  })

  const initiatePayment = useMutation({
    mutationFn: () => marketApi.initiateAssignmentPayment(assignmentId),
    onSuccess: (payment) => setClientSecret(payment.client_secret),
    onError: (err) => {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined
      toast.error(
        typeof detail === 'object' && detail?.message ? detail.message : 'Failed to initiate payment',
      )
    },
  })

  const declineAssignment = useMutation({
    mutationFn: () => marketApi.declineAssignment(assignmentId),
    onSuccess: () => {
      toast.success('Assignment declined')
      void queryClient.invalidateQueries({ queryKey: ['market'] })
      void navigate({ to: '/market' })
    },
    onError: () => toast.error('Failed to decline assignment'),
  })

  const handleAccept = async () => {
    await saveHolders.mutateAsync()
    initiatePayment.mutate()
  }

  const handlePaySuccess = () => {
    toast.success('Payment successful — ticket is being transferred!')
    void queryClient.invalidateQueries({ queryKey: ['tickets'] })
    void queryClient.invalidateQueries({ queryKey: ['market'] })
    void navigate({ to: '/tickets' })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen pb-32">
        <Skeleton className="h-64 w-full rounded-none" />
        <div className="mx-auto max-w-[430px] space-y-2 px-4 pt-4 pb-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-3 w-40" />
        </div>
        <div className="mx-auto mt-5 max-w-[430px] space-y-3 rounded-2xl border border-white/10 bg-white/5 p-5">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-10 w-full rounded-full" />
        </div>
      </div>
    )
  }

  if (isError || !assignment) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <ShieldX className="h-10 w-10 text-white/30" />
        <p className="text-muted-foreground text-sm">Assignment not found or already handled.</p>
      </div>
    )
  }

  const isPaid = assignment.state === 'paid'
  const isExpired = assignment.state === 'expired'
  const isDeclined = assignment.state === 'declined'
  const countdownExpired = countdown === 0 && assignment.state === 'pending'
  const isPending = assignment.state === 'pending' && !countdownExpired

  const nameOk = holderName.trim().length > 0
  const dniOk = validateDni(holderDni)
  const holdersComplete = nameOk && dniOk
  const accepting = saveHolders.isPending || initiatePayment.isPending

  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? assignment.event_name ?? 'Event ticket'
  const startDate = event?.starts_at ? new Date(event.starts_at) : null

  return (
    <div className="min-h-screen pb-32">
      {/* Hero image — same treatment as event detail page */}
      <div className="relative h-64 overflow-hidden bg-[#111]">
        <ImageWithSkeleton
          src={imageUrl}
          alt={eventName}
          className={cn(
            'absolute inset-0 h-full w-full',
            event?.image_url ? 'object-cover opacity-80' : 'object-contain p-8 opacity-60',
          )}
        />
        {event?.image_url && (
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 to-transparent" />
        )}
        {/* bottom fade into page background */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[hsl(0,0%,10%)] to-transparent" />

        <BackButton to="/market" className="absolute top-4 left-4" />

        <div className="absolute top-4 right-4 flex items-center gap-2">
          <StatusChip label="Resale" variant="reserved" />
          {isPending && (
            <div className="flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 backdrop-blur-sm">
              <Clock className="h-3 w-3 text-yellow-400" />
              <span className="font-mono text-xs font-semibold text-yellow-400">
                {formatSeconds(countdown)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Event info */}
      <div className="mx-auto max-w-[430px] space-y-1 px-4 pb-4">
        <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
          {event?.organisation?.name ?? event?.organiser_name ?? 'Resale Market'}
        </p>
        <h1 className="text-2xl font-bold">{eventName}</h1>
        <div className="text-muted-foreground flex flex-wrap gap-3 pt-1 text-sm">
          {event?.venue_city && (
            <span className="flex items-center gap-1.5">
              <MapPin className="h-4 w-4 shrink-0" />
              {event.venue_city}
            </span>
          )}
          {startDate && (
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4 shrink-0" />
              {startDate.toLocaleDateString('en-GB', {
                weekday: 'short',
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}
        </div>

        {/* Ticket details card */}
        <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
          <div className="space-y-0.5">
            <p className="text-muted-foreground text-xs uppercase tracking-wide">Ticket type</p>
            <p className="text-sm font-semibold">{assignment.ticket_type_name ?? 'General Admission'}</p>
          </div>
          <div className="text-right space-y-0.5">
            <p className="text-muted-foreground text-xs uppercase tracking-wide">Price</p>
            <p className="text-lg font-bold text-yellow-400">
              {formatPrice(assignment.price_cents, assignment.currency)}
            </p>
          </div>
        </div>
      </div>

      {/* Pending — holder form + actions */}
      {isPending && !clientSecret && (
        <div className="mx-auto mt-5 max-w-[430px] space-y-4 px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5 space-y-4">
            <div>
              <p className="text-sm font-semibold">Who&apos;s attending?</p>
              <p className="text-muted-foreground mt-0.5 text-xs">
                You&apos;ve been assigned a resale ticket. Fill in the details to accept.
              </p>
            </div>

            <div className="space-y-2">
              <input
                type="text"
                placeholder="Full name"
                value={holderName}
                onChange={(e) => setHolderName(e.target.value)}
                className="placeholder:text-muted-foreground w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white focus:border-white/30 focus:outline-none"
              />
              <div>
                <input
                  type="text"
                  placeholder="DNI / NIE"
                  value={holderDni}
                  onChange={(e) => setHolderDni(e.target.value)}
                  className={cn(
                    'placeholder:text-muted-foreground w-full rounded-xl border bg-white/5 px-4 py-2.5 text-sm text-white focus:outline-none',
                    holderDni && !validateDni(holderDni)
                      ? 'border-red-500/60 focus:border-red-500/80'
                      : 'border-white/10 focus:border-white/30',
                  )}
                />
                {holderDni && !validateDni(holderDni) && (
                  <p className="mt-1 px-1 text-xs text-red-400">Invalid DNI / NIE</p>
                )}
              </div>
            </div>

            <button
              onClick={() => void handleAccept()}
              disabled={!holdersComplete || accepting}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-yellow-400 py-3 text-sm font-semibold text-black disabled:opacity-40"
            >
              {accepting ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" />
              ) : (
                <CreditCard className="h-4 w-4" />
              )}
              Accept &amp; Pay
            </button>
          </div>

          <button
            onClick={() => declineAssignment.mutate()}
            disabled={declineAssignment.isPending}
            className="w-full rounded-full border border-red-500/30 py-3 text-sm font-medium text-red-400 transition hover:bg-red-500/10 disabled:opacity-40"
          >
            Decline
          </button>
        </div>
      )}

      {/* Stripe checkout */}
      {clientSecret && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <StripeCheckout clientSecret={clientSecret} onSuccess={handlePaySuccess} />
        </div>
      )}

      {/* Terminal states */}
      {isPaid && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-green-400/20 bg-green-400/5 p-6 text-center">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
            <p className="text-sm font-semibold text-green-400">Payment confirmed</p>
            <p className="text-muted-foreground text-xs">Your ticket is being transferred.</p>
          </div>
        </div>
      )}
      {(isExpired || countdownExpired) && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-sm font-semibold text-white/60">This assignment has expired.</p>
            <p className="text-muted-foreground mt-1 text-xs">
              You&apos;ve been removed from the queue. Rejoin if you want another chance.
            </p>
          </div>
        </div>
      )}
      {isDeclined && (
        <div className="mx-auto mt-5 max-w-[430px] px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-muted-foreground text-sm">Assignment declined.</p>
          </div>
        </div>
      )}
    </div>
  )
}
