// renders the ticket type list component
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyMessage } from '@/components/ui/empty-message'
import { ListError } from '@/components/ui/list-error'
import { TicketTypeListSkeleton } from '@/components/ui/skeleton'

import { useDeleteTicketType } from '../hooks/useDeleteTicketType'
import { useOrgTicketTypes } from '../hooks/useOrgTicketTypes'
import { AddTicketTypeForm } from './AddTicketTypeForm'
import { CapacityEditTicketTypeForm, EditTicketTypeForm } from './EditTicketTypeForm'

interface Props {
  eventId: string
  eventStatus?: 'draft' | 'published' | 'ongoing' | 'cancelled'
}

// renders the ticket type list component
export function TicketTypeList({ eventId, eventStatus = 'draft' }: Props) {
  const { t } = useTranslation()
  const { data, isLoading, isError, refetch } = useOrgTicketTypes(eventId)
  const deleteTt = useDeleteTicketType(eventId)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const ticketTypes = data?.items ?? []

  const canEdit = eventStatus === 'draft'
  const canEditCapacity = eventStatus === 'published'
  const canAdd = eventStatus === 'draft' || eventStatus === 'published'

  if (isLoading) {
    return <TicketTypeListSkeleton />
  }

  if (isError) {
    return <ListError onRetry={() => void refetch()} />
  }

  return (
    <div className="space-y-4">
      {ticketTypes.length === 0 && <EmptyMessage>{t('organiser.ticketTypes.empty')}</EmptyMessage>}
      {ticketTypes.map((tt) =>
        canEdit && editingId === tt.id ? (
          <EditTicketTypeForm
            key={tt.id}
            ttId={tt.id}
            eventId={eventId}
            defaultValues={{
              name: tt.name,
              description: tt.description ?? '',
              capacity: tt.capacity,
              price_cents: tt.price_cents / 100,
              position: tt.position,
            }}
            onClose={() => setEditingId(null)}
          />
        ) : canEditCapacity && editingId === tt.id ? (
          <CapacityEditTicketTypeForm
            key={tt.id}
            ttId={tt.id}
            eventId={eventId}
            currentCapacity={tt.capacity}
            onClose={() => setEditingId(null)}
          />
        ) : (
          <div
            key={tt.id}
            className="relative flex overflow-hidden rounded-2xl bg-white text-gray-900 shadow-sm"
          >
            <div
              className="absolute top-0 z-10 h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{ left: 'calc(100% - 5rem)', backgroundColor: 'hsl(0, 0%, 10%)' }}
            />
            <div
              className="absolute bottom-0 z-10 h-6 w-6 -translate-x-1/2 translate-y-1/2 rounded-full"
              style={{ left: 'calc(100% - 5rem)', backgroundColor: 'hsl(0, 0%, 10%)' }}
            />

            <div className="flex min-w-0 flex-1 items-center gap-2 py-6 pr-3 pl-5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold capitalize">{tt.name}</p>
                <p className="mt-0.5 text-xs text-gray-500">
                  {t('organiser.ticketTypes.available', {
                    available: tt.available,
                    capacity: tt.capacity,
                  })}
                </p>
              </div>
              {(canEdit || canEditCapacity) && (
                <div className="flex shrink-0 items-center gap-0.5">
                  <button
                    onClick={() => setEditingId(tt.id)}
                    className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {canEdit && (
                    <button
                      onClick={() => setConfirmDeleteId(tt.id)}
                      className="rounded-lg p-1.5 text-red-400 transition-colors hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="my-4 border-l border-dashed border-gray-400" />

            <div className="flex w-20 shrink-0 flex-col items-center justify-center px-2 py-6">
              {tt.price_cents === 0 ? (
                <p className="text-xs font-semibold text-green-600">
                  {t('organiser.ticketTypes.free')}
                </p>
              ) : (
                <>
                  <p className="text-sm font-bold tabular-nums">
                    {(tt.price_cents / 100).toFixed(2)}
                  </p>
                  <p className="text-[10px] tracking-wide text-gray-500 uppercase">{tt.currency}</p>
                </>
              )}
            </div>
          </div>
        ),
      )}

      <ConfirmDialog
        open={confirmDeleteId !== null}
        onOpenChange={(next) => !next && setConfirmDeleteId(null)}
        tone="destructive"
        icon={Trash2}
        title={t('organiser.ticketTypes.deleteTitle')}
        description={t('organiser.ticketTypes.deleteDesc')}
        irreversible
        confirmLabel={t('organiser.ticketTypes.deleteConfirm')}
        isLoading={deleteTt.isPending}
        onConfirm={() => confirmDeleteId && deleteTt.mutate(confirmDeleteId)}
      />

      {canAdd &&
        (showAdd ? (
          <AddTicketTypeForm eventId={eventId} onClose={() => setShowAdd(false)} />
        ) : (
          <div className="flex justify-end">
            <button
              onClick={() => setShowAdd(true)}
              className="bg-primary hover:bg-primary/90 flex h-10 items-center gap-2 rounded-full px-5 text-sm font-semibold text-white transition-colors"
            >
              <Plus className="h-4 w-4" />
              {t('organiser.ticketTypes.addButton')}
            </button>
          </div>
        ))}
    </div>
  )
}
