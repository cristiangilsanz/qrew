import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { Calendar, LogOut, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { BackButton } from '@/components/ui/back-button'
import { ImageWithSkeleton } from '@/components/ui/image-with-skeleton'
import { WaitlistRowSkeleton } from '@/components/ui/skeleton'
import { useEvent } from '@/features/events/hooks/useEvent'
import { marketApi } from '@/features/market/api'
import { useMyQueues } from '@/features/market/hooks/useMyQueues'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/market/waitlists/')({
  component: WaitlistsPage,
})

function WaitlistRow({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: event, isLoading: eventLoading } = useEvent(eventId)
  const imageUrl = getEventImageUrl(event?.image_url)
  const eventName = event?.name ?? ''
  const [leaveOpen, setLeaveOpen] = useState(false)

  const leaveQueue = useMutation({
    mutationFn: () => marketApi.leaveQueue(eventId),
    onSuccess: () => {
      toast.success(t('market.toast.leftWaitlist'))
      setLeaveOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['market', 'queues'] })
      void queryClient.invalidateQueries({ queryKey: ['market', 'queue', eventId] })
    },
    onError: () => toast.error(t('market.toast.leaveFailed')),
  })

  if (eventLoading) return <WaitlistRowSkeleton />

  return (
    <>
      <div className="bg-card border-border overflow-hidden rounded-xl border">
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
            onClick={() => setLeaveOpen(true)}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500 transition-colors hover:bg-red-600"
          >
            <LogOut className="h-3.5 w-3.5 text-white" />
          </button>
        </div>
      </div>

      <AnimatePresence>
        {leaveOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setLeaveOpen(false)}
          >
            <motion.div
              initial={{ y: 32, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 32, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="w-full max-w-sm rounded-2xl border border-red-500/20 bg-[#111] p-6"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                  <LogOut className="h-5 w-5 text-red-400" />
                </div>
                <h3 className="text-base font-semibold text-red-400">
                  {t('market.leaveQueue.title')}
                </h3>
              </div>
              <p className="text-muted-foreground mb-6 text-sm">
                {t('market.leaveQueue.description')}
              </p>
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setLeaveOpen(false)}
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => leaveQueue.mutate()}
                  disabled={leaveQueue.isPending}
                  className="flex h-10 min-w-[120px] items-center justify-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {leaveQueue.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      <LogOut className="h-3.5 w-3.5" />
                      {t('market.leaveQueue.confirm')}
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function WaitlistsPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const { data: queues, isLoading } = useMyQueues()

  const filtered = (queues ?? []).filter(
    (entry) => !query || entry.event_id.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <div className="mx-auto min-h-screen max-w-[430px] space-y-4 px-4 pt-5 pb-28">
      <div>
        <BackButton to="/market" />
        <h1 className="mt-3 text-2xl font-bold">{t('market.myWaitlists')}</h1>
      </div>

      {!isLoading && (queues ?? []).length > 0 && (
        <div className="relative">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            placeholder={t('market.searchByEvent')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pr-4 pl-9 text-sm text-white placeholder:text-white/30 focus:border-white/20 focus:outline-none"
          />
        </div>
      )}

      {isLoading && (
        <div className="space-y-3">
          <WaitlistRowSkeleton />
          <WaitlistRowSkeleton />
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <p className="text-muted-foreground pt-10 text-center text-sm">
          {query ? t('market.noResults') : t('market.noWaitlists')}
        </p>
      )}

      <div className="space-y-3">
        {filtered.map((entry) => (
          <WaitlistRow key={entry.event_id} eventId={entry.event_id} />
        ))}
      </div>
    </div>
  )
}
