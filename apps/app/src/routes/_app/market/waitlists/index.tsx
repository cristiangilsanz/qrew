// implements waitlists
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Calendar, LogOut, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyMessage } from '@/components/ui/empty-message'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { PageError } from '@/components/ui/page-error'
import { SEARCH_ICON_CLASS, SEARCH_INPUT_CLASS } from '@/components/ui/search-field'
import { WaitlistRowSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMyQueues } from '@/features/market/hooks/useMyQueues'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/waitlists/')({
  component: WaitlistsPage,
})

// renders the waitlist row component
function WaitlistRow({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: event, isLoading: eventLoading } = useEvent(eventId)
  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? ''
  const [leaveOpen, setLeaveOpen] = useState(false)

  const leaveQueue = useMutation({
    // implements mutation fn
    mutationFn: () => marketApi.leaveQueue(eventId),
    // handles on success
    onSuccess: () => {
      toast.success(t('market.toast.leftWaitlist'))
      setLeaveOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['market', 'queues'] })
      void queryClient.invalidateQueries({ queryKey: ['market', 'queue', eventId] })
    },
    // handles on error
    onError: () => toast.error(t('market.toast.leaveFailed')),
  })

  if (eventLoading) return <WaitlistRowSkeleton />

  return (
    <>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */}
      <article
        onClick={() => void navigate({ to: '/events/$eventId', params: { eventId } })}
        className="bg-card border-border hover:border-primary cursor-pointer overflow-hidden rounded-xl border transition-colors"
      >
        <div className="relative h-24 w-full overflow-hidden bg-[#111]">
          <ImageWithSkeleton
            src={imageUrl}
            alt={eventName}
            className={cn(
              'h-full w-full',
              event?.image_url ? 'object-cover opacity-70' : 'object-contain p-3 opacity-50',
            )}
          />
          {event?.image_url && (
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          )}
        </div>
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {event?.organisation?.name ?? t('market.resaleMarket')}
            </p>
            <p className="truncate text-sm font-semibold">{eventName}</p>
            {event?.starts_at && (
              <p className="text-muted-foreground mt-0.5 flex items-center gap-1 text-xs">
                <Calendar className="h-3 w-3 shrink-0" />
                {new Date(event.starts_at).toLocaleDateString('en-GB', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric',
                })}
              </p>
            )}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              setLeaveOpen(true)
            }}
            className="flex h-8 shrink-0 items-center gap-1.5 rounded-full border border-red-500/25 bg-red-500/15 px-3 text-xs font-semibold text-red-400"
          >
            <LogOut className="h-3.5 w-3.5 shrink-0" />
            {t('market.leaveWaitlistButton')}
          </button>
        </div>
      </article>

      <ConfirmDialog
        open={leaveOpen}
        onOpenChange={setLeaveOpen}
        tone="destructive"
        icon={LogOut}
        title={t('market.leaveWaitlist.title')}
        description={t('market.leaveWaitlist.description')}
        irreversible
        confirmLabel={t('market.leaveWaitlist.confirm')}
        isLoading={leaveQueue.isPending}
        onConfirm={() => leaveQueue.mutate()}
      />
    </>
  )
}

// renders the waitlists page component
function WaitlistsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: queues, isLoading, isError, refetch } = useMyQueues()

  // implements filtered
  const filtered = (queues ?? []).filter(
    (entry) => !query || entry.event_id.toLowerCase().includes(query.toLowerCase()),
  )

  if (isError) return <PageError onRetry={() => void refetch()} />

  return (
    <div className="mx-auto max-w-[430px] space-y-4 px-4 pt-5 pb-28">
      <BackButton to="/market" />
      <h1 className="text-2xl font-bold">{t('market.myWaitlists')}</h1>

      {!isLoading && (queues ?? []).length > 0 && (
        <div className="relative">
          <Search className={SEARCH_ICON_CLASS} />
          <input
            type="text"
            placeholder={t('market.searchByEvent')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={SEARCH_INPUT_CLASS}
          />
        </div>
      )}

      {isLoading && (
        <div className="space-y-3">
          <WaitlistRowSkeleton />
          <WaitlistRowSkeleton />
        </div>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyMessage>{query ? t('market.noResults') : t('market.noWaitlists')}</EmptyMessage>
      )}

      <div className="space-y-3">
        {filtered.map((entry) => (
          <WaitlistRow key={entry.event_id} eventId={entry.event_id} />
        ))}
      </div>
    </div>
  )
}
