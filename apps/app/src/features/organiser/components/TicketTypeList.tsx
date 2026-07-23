import { zodResolver } from '@hookform/resolvers/zod'
import { AnimatePresence, motion } from 'framer-motion'
import { Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { TicketTypeListSkeleton } from '@/components/ui/skeleton'

import { useCreateTicketType } from '../hooks/useCreateTicketType'
import { useDeleteTicketType } from '../hooks/useDeleteTicketType'
import { useOrgTicketTypes } from '../hooks/useOrgTicketTypes'
import { useUpdateTicketType } from '../hooks/useUpdateTicketType'

const createSchema = z.object({
  name: z
    .string()
    .min(1)
    .max(32)
    .transform((v) => v.toLowerCase())
    .pipe(
      z
        .string()
        .regex(/^[a-z][a-z0-9_]{0,31}$/, 'Must start with a letter, no spaces or special chars'),
    ),
  description: z.string().optional(),
  capacity: z.coerce.number().int().min(1).max(100000),
  price_cents: z.coerce.number().min(0).max(100000).transform((v) => Math.round(v * 100)),
  currency: z.literal('EUR').default('EUR'),
  position: z.coerce.number().int().optional(),
})

const editSchema = z.object({
  name: z
    .string()
    .min(1)
    .max(32)
    .transform((v) => v.toLowerCase())
    .pipe(
      z
        .string()
        .regex(/^[a-z][a-z0-9_]{0,31}$/, 'Must start with a letter, no spaces or special chars'),
    ),
  description: z.string().optional(),
  capacity: z.coerce.number().int().min(1).max(100000),
  price_cents: z.coerce.number().min(0).max(100000).transform((v) => Math.round(v * 100)),
  position: z.coerce.number().int().optional(),
})

type CreateValues = z.infer<typeof createSchema>
type EditValues = z.infer<typeof editSchema>

interface EditRowProps {
  ttId: string
  eventId: string
  defaultValues: EditValues
  onClose: () => void
}

function EditRow({ ttId, eventId, defaultValues, onClose }: EditRowProps) {
  const { t } = useTranslation()
  const updateTt = useUpdateTicketType(eventId)
  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues,
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          updateTt.mutate({ ttId, data: v })
          onClose()
        })}
        className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5"
      >
        <p className="text-sm font-semibold">{t('organiser.ticketTypes.title')}</p>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.nameLabel')}</FormLabel>
              <FormControl>
                <input className={darkInput} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="capacity"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.ticketTypes.capacityLabel')}</FormLabel>
                <FormControl>
                  <input type="number" className={darkInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="price_cents"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.ticketTypes.priceLabel')} (€)</FormLabel>
                <FormControl>
                  <input type="number" step="0.01" min="0" placeholder="0.00" className={darkInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="position"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.positionLabel')}</FormLabel>
              <FormControl>
                <input type="number" className={darkInput} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-between pt-1">
          <button
            type="button"
            className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <Button type="submit" isLoading={updateTt.isPending} className="rounded-full px-6">
            <RefreshCw className="h-4 w-4" />
            {t('organiser.events.updateEvent')}
          </Button>
        </div>
      </form>
    </Form>
  )
}

const capacitySchema = z.object({
  capacity: z.coerce.number().int().min(1).max(100000),
})
type CapacityValues = z.infer<typeof capacitySchema>

interface CapacityEditRowProps {
  ttId: string
  eventId: string
  currentCapacity: number
  onClose: () => void
}

function CapacityEditRow({ ttId, eventId, currentCapacity, onClose }: CapacityEditRowProps) {
  const { t } = useTranslation()
  const updateTt = useUpdateTicketType(eventId)
  const form = useForm<CapacityValues>({
    resolver: zodResolver(capacitySchema),
    defaultValues: { capacity: currentCapacity },
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          updateTt.mutate({ ttId, data: { capacity: v.capacity } })
          onClose()
        })}
        className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5"
      >
        <FormField
          control={form.control}
          name="capacity"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.capacityLabel')}</FormLabel>
              <FormControl>
                <input type="number" className={darkInput} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-between pt-1">
          <button
            type="button"
            className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <Button type="submit" isLoading={updateTt.isPending} className="rounded-full px-6">
            <RefreshCw className="h-4 w-4" />
            {t('organiser.events.updateEvent')}
          </Button>
        </div>
      </form>
    </Form>
  )
}

interface AddFormProps {
  eventId: string
  onClose: () => void
}

const darkInput =
  'border-white/15 bg-white/5 text-white placeholder:text-white/30 focus:border-primary/60 w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-colors'

function AddForm({ eventId, onClose }: AddFormProps) {
  const { t } = useTranslation()
  const createTt = useCreateTicketType(eventId)
  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: '', description: '', capacity: 100, price_cents: 0 },
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          createTt.mutate(v)
          form.reset()
          onClose()
        })}
        className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-5"
      >
        <p className="text-sm font-semibold">{t('organiser.ticketTypes.addButton')}</p>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.ticketTypes.nameLabel')}</FormLabel>
              <FormControl>
                <input className={darkInput} placeholder="General Admission" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="capacity"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.ticketTypes.capacityLabel')}</FormLabel>
                <FormControl>
                  <input type="number" className={darkInput} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="price_cents"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('organiser.ticketTypes.priceLabel')} (€)</FormLabel>
                <FormControl>
                  <input type="number" step="0.01" min="0" className={darkInput} placeholder="0.00" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="flex justify-between pt-1">
          <button
            type="button"
            className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <Button type="submit" isLoading={createTt.isPending} className="rounded-full px-6">
            <Plus className="h-4 w-4" />
            {t('organiser.ticketTypes.addButton')}
          </Button>
        </div>
      </form>
    </Form>
  )
}

interface Props {
  eventId: string
  eventStatus?: 'draft' | 'published' | 'cancelled'
}

export function TicketTypeList({ eventId, eventStatus = 'draft' }: Props) {
  const { t } = useTranslation()
  const { data, isLoading } = useOrgTicketTypes(eventId)
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

  return (
    <div className="space-y-4">
      {ticketTypes.map((tt) =>
        canEdit && editingId === tt.id ? (
          <EditRow
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
          <CapacityEditRow
            key={tt.id}
            ttId={tt.id}
            eventId={eventId}
            currentCapacity={tt.capacity}
            onClose={() => setEditingId(null)}
          />
        ) : (
          /* Ticket-shaped card — white background with top/bottom notch semicircles */
          <div
            key={tt.id}
            className="relative flex overflow-hidden rounded-2xl bg-white text-gray-900 shadow-sm"
          >
            {/* Notch semicircles — match the container bg-white/5 over the page background */}
            <div
              className="absolute top-0 z-10 h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{ left: 'calc(100% - 5rem)', backgroundColor: 'hsl(0, 0%, 10%)' }}
            />
            <div
              className="absolute bottom-0 z-10 h-6 w-6 -translate-x-1/2 translate-y-1/2 rounded-full"
              style={{ left: 'calc(100% - 5rem)', backgroundColor: 'hsl(0, 0%, 10%)' }}
            />

            {/* Left section: info + action buttons */}
            <div className="flex min-w-0 flex-1 items-center gap-2 py-6 pl-5 pr-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold capitalize">{tt.name}</p>
                <p className="mt-0.5 text-xs text-gray-500">
                  {t('organiser.ticketTypes.available', { available: tt.available, capacity: tt.capacity })}
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

            {/* Dashed vertical separator */}
            <div className="my-4 border-l border-dashed border-gray-400" />

            {/* Price stub — fixed w-20 so notch circles align */}
            <div className="flex w-20 shrink-0 flex-col items-center justify-center px-2 py-6">
              {tt.price_cents === 0 ? (
                <p className="text-xs font-semibold text-green-600">{t('organiser.ticketTypes.free')}</p>
              ) : (
                <>
                  <p className="text-sm font-bold tabular-nums">
                    {(tt.price_cents / 100).toFixed(2)}
                  </p>
                  <p className="text-[10px] uppercase tracking-wide text-gray-500">{tt.currency}</p>
                </>
              )}
            </div>
          </div>
        ),
      )}

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {confirmDeleteId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center"
            style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            onClick={(e) => e.target === e.currentTarget && setConfirmDeleteId(null)}
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
                  <Trash2 className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-red-400">
                    {t('organiser.ticketTypes.deleteTitle')}
                  </h3>
                  <p className="text-muted-foreground text-xs capitalize">
                    {ticketTypes.find((tt) => tt.id === confirmDeleteId)?.name ?? '—'}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black"
                  onClick={() => setConfirmDeleteId(null)}
                >
                  {t('common.goBack')}
                </button>
                <button
                  onClick={() => {
                    deleteTt.mutate(confirmDeleteId)
                    setConfirmDeleteId(null)
                  }}
                  disabled={deleteTt.isPending}
                  className="flex h-10 items-center gap-2 rounded-full bg-red-500 px-5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {deleteTt.isPending ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" />
                  )}
                  {t('organiser.ticketTypes.deleteConfirm')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add ticket type */}
      {canAdd &&
        (showAdd ? (
          <AddForm eventId={eventId} onClose={() => setShowAdd(false)} />
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
