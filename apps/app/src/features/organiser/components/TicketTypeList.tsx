import { zodResolver } from '@hookform/resolvers/zod'
import { Pencil, Trash2 } from 'lucide-react'
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
import { Input } from '@/components/ui/input'

import { useCreateTicketType } from '../hooks/useCreateTicketType'
import { useDeleteTicketType } from '../hooks/useDeleteTicketType'
import { useOrgTicketTypes } from '../hooks/useOrgTicketTypes'
import { useUpdateTicketType } from '../hooks/useUpdateTicketType'

const createSchema = z.object({
  name: z.string().min(1).max(32),
  description: z.string().optional(),
  capacity: z.coerce.number().int().min(1).max(100000),
  price_cents: z.coerce.number().int().min(0).max(10000000),
  currency: z.string().length(3),
  position: z.coerce.number().int().optional(),
})

const editSchema = z.object({
  name: z.string().min(1).max(32),
  description: z.string().optional(),
  capacity: z.coerce.number().int().min(1).max(100000),
  price_cents: z.coerce.number().int().min(0).max(10000000),
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
        className="space-y-2 rounded-md border p-3"
      >
        <div className="grid grid-cols-2 gap-2">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs">{t('organiser.ticketTypes.nameLabel')}</FormLabel>
                <FormControl>
                  <Input className="h-8 text-sm" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="capacity"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs">
                  {t('organiser.ticketTypes.capacityLabel')}
                </FormLabel>
                <FormControl>
                  <Input type="number" className="h-8 text-sm" {...field} />
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
                <FormLabel className="text-xs">{t('organiser.ticketTypes.priceLabel')}</FormLabel>
                <FormControl>
                  <Input type="number" className="h-8 text-sm" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="position"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs">
                  {t('organiser.ticketTypes.positionLabel')}
                </FormLabel>
                <FormControl>
                  <Input type="number" className="h-8 text-sm" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="flex gap-2">
          <Button type="submit" size="sm" isLoading={updateTt.isPending}>
            {t('common.save')}
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={onClose}>
            {t('common.cancel')}
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

function AddForm({ eventId, onClose }: AddFormProps) {
  const { t } = useTranslation()
  const createTt = useCreateTicketType(eventId)
  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: '', description: '', capacity: 100, price_cents: 0, currency: 'EUR' },
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          createTt.mutate(v)
          form.reset()
          onClose()
        })}
        className="space-y-2 rounded-md border p-3"
      >
        <div className="grid grid-cols-2 gap-2">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs">{t('organiser.ticketTypes.nameLabel')}</FormLabel>
                <FormControl>
                  <Input className="h-8 text-sm" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="capacity"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs">
                  {t('organiser.ticketTypes.capacityLabel')}
                </FormLabel>
                <FormControl>
                  <Input type="number" className="h-8 text-sm" {...field} />
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
                <FormLabel className="text-xs">{t('organiser.ticketTypes.priceLabel')}</FormLabel>
                <FormControl>
                  <Input type="number" className="h-8 text-sm" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="currency"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-xs">
                  {t('organiser.ticketTypes.currencyLabel')}
                </FormLabel>
                <FormControl>
                  <Input className="h-8 text-sm" maxLength={3} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="flex gap-2">
          <Button type="submit" size="sm" isLoading={createTt.isPending}>
            {t('common.save')}
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={onClose}>
            {t('common.cancel')}
          </Button>
        </div>
      </form>
    </Form>
  )
}

interface Props {
  eventId: string
}

export function TicketTypeList({ eventId }: Props) {
  const { t } = useTranslation()
  const { data, isLoading } = useOrgTicketTypes(eventId)
  const deleteTt = useDeleteTicketType(eventId)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const ticketTypes = data?.items ?? []

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="border-primary h-6 w-6 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {ticketTypes.map((tt) =>
        editingId === tt.id ? (
          <EditRow
            key={tt.id}
            ttId={tt.id}
            eventId={eventId}
            defaultValues={{
              name: tt.name,
              description: tt.description ?? '',
              capacity: tt.capacity,
              price_cents: tt.price_cents,
              position: tt.position,
            }}
            onClose={() => setEditingId(null)}
          />
        ) : (
          <div key={tt.id} className="flex items-center justify-between rounded-md border p-3">
            <div>
              <p className="font-medium">{tt.name}</p>
              <p className="text-muted-foreground text-xs">
                {(tt.price_cents / 100).toFixed(2)} {tt.currency} · {tt.available}/{tt.capacity}{' '}
                available
              </p>
            </div>
            <div className="flex gap-1">
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8"
                onClick={() => setEditingId(tt.id)}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
              {confirmDeleteId === tt.id ? (
                <>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="h-8"
                    onClick={() => {
                      deleteTt.mutate(tt.id)
                      setConfirmDeleteId(null)
                    }}
                    isLoading={deleteTt.isPending}
                  >
                    {t('common.save')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8"
                    onClick={() => setConfirmDeleteId(null)}
                  >
                    {t('common.cancel')}
                  </Button>
                </>
              ) : (
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={() => setConfirmDeleteId(tt.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
        ),
      )}
      {showAdd ? (
        <AddForm eventId={eventId} onClose={() => setShowAdd(false)} />
      ) : (
        <Button size="sm" variant="outline" onClick={() => setShowAdd(true)}>
          {t('organiser.ticketTypes.addButton')}
        </Button>
      )}
    </div>
  )
}
