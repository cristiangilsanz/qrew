import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
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

import type { Organisation } from '../api'
import { useCreateOrganisation } from '../hooks/useCreateOrganisation'

const schema = z.object({
  slug: z
    .string()
    .regex(
      /^[a-z][a-z0-9_-]{2,63}$/,
      'Must start with a letter, 3–64 chars, lowercase letters/numbers/hyphens/underscores only',
    ),
  name: z.string().min(1).max(128),
  description: z.string().optional(),
})

type Values = z.infer<typeof schema>

interface Props {
  onSuccess?: (orgId: string) => void
}

export function CreateOrganisationForm({ onSuccess }: Props) {
  const { t } = useTranslation()

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { slug: '', name: '', description: '' },
  })

  const createOrg = useCreateOrganisation((org: Organisation) => {
    form.reset()
    onSuccess?.(org.id)
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((v) => createOrg.mutate(v))} className="space-y-3">
        <FormField
          control={form.control}
          name="slug"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.org.slugLabel')}</FormLabel>
              <FormControl>
                <Input placeholder={t('organiser.org.slugPlaceholder')} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.org.nameLabel')}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.org.descriptionLabel')}</FormLabel>
              <FormControl>
                <textarea
                  rows={3}
                  className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex min-h-[60px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Button type="submit" isLoading={createOrg.isPending} className="rounded-full px-6">
            <Plus className="h-4 w-4" />
            {t('organiser.org.create')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
