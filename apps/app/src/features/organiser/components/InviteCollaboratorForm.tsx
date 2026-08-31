// renders the invite member form component
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { Info, Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
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
import {
  SEARCH_CLEAR_CLASS,
  SEARCH_ICON_CLASS,
  SEARCH_INPUT_CLASS,
} from '@/components/ui/search-field'
import { profileApi } from '@/features/profile/api'
import { cn } from '@/lib/utils'

import { useInviteCollaborator } from '../hooks/useInviteCollaborator'

const schema = z.object({
  user_id: z.string().uuid(),
  role: z.enum(['member', 'manager']),
})

type Values = z.infer<typeof schema>

const MIN_QUERY_LENGTH = 2

interface Props {
  orgId: string
  existingCollaboratorIds?: string[]
  onSuccess?: () => void
}

// renders the invite member form component
export function InviteCollaboratorForm({ orgId, existingCollaboratorIds = [], onSuccess }: Props) {
  const { t } = useTranslation()
  const [searchQ, setSearchQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // implements timer
    const timer = setTimeout(() => setDebouncedQ(searchQ), 300)
    return () => clearTimeout(timer)
  }, [searchQ])

  const term = debouncedQ.trim()
  const canSearch = term.length >= MIN_QUERY_LENGTH

  const { data: matches = [], isFetching } = useQuery({
    queryKey: ['user-search', term],
    // implements query fn
    queryFn: () => profileApi.searchUsers(term),
    enabled: canSearch,
    staleTime: 30_000,
  })

  // implements filtered
  const filtered = matches.filter((u) => !existingCollaboratorIds.includes(u.id))

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { user_id: '', role: 'member' },
  })

  const invite = useInviteCollaborator(orgId)

  useEffect(() => {
    // handles on click outside
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  // implements select user
  function selectUser(id: string, email: string) {
    form.setValue('user_id', id, { shouldValidate: true })
    setSearchQ(email)
    setDropdownOpen(false)
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => {
          invite.mutate(v, {
            // handles on success
            onSuccess: () => {
              form.reset()
              setSearchQ('')
              onSuccess?.()
            },
          })
        })}
        className="w-full space-y-4"
      >
        <input type="hidden" {...form.register('user_id')} />

        <FormItem>
          <FormLabel>{t('organiser.collaborators.emailLabel')}</FormLabel>
          <div ref={containerRef} className="relative">
            <Search className={SEARCH_ICON_CLASS} />
            <input
              type="search"
              autoComplete="off"
              className={SEARCH_INPUT_CLASS}
              placeholder={t('organiser.collaborators.emailPlaceholder')}
              value={searchQ}
              onChange={(e) => {
                setSearchQ(e.target.value)
                form.setValue('user_id', '', { shouldValidate: false })
                setDropdownOpen(true)
              }}
              onFocus={() => setDropdownOpen(true)}
            />
            {searchQ && (
              <button
                type="button"
                onClick={() => {
                  setSearchQ('')
                  form.setValue('user_id', '', { shouldValidate: false })
                }}
                className={SEARCH_CLEAR_CLASS}
              >
                <X className="h-4 w-4" />
              </button>
            )}
            {dropdownOpen && canSearch && (
              <ul className="absolute z-50 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-white/15 bg-black/95 shadow-xl backdrop-blur-md">
                {isFetching && filtered.length === 0 && (
                  <li className="text-muted-foreground px-4 py-3 text-xs">{t('common.loading')}</li>
                )}
                {!isFetching && filtered.length === 0 && (
                  <li className="text-muted-foreground px-4 py-3 text-xs">
                    {t('organiser.collaborators.noMatches')}
                  </li>
                )}
                {filtered.map((u) => (
                  <li key={u.id}>
                    <button
                      type="button"
                      className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.06]"
                      onMouseDown={(e) => {
                        e.preventDefault()
                        selectUser(u.id, u.email)
                      }}
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold uppercase">
                        {u.full_name.slice(0, 2)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{u.full_name}</p>
                        <p className="text-muted-foreground truncate text-xs">{u.email}</p>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {form.formState.errors.user_id && (
            <p className="text-destructive text-sm">{t('organiser.collaborators.selectUser')}</p>
          )}
        </FormItem>
        <FormField
          control={form.control}
          name="role"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.collaborators.roleLabel')}</FormLabel>
              <FormControl>
                <div className="grid grid-cols-2 items-stretch gap-2">
                  {(['manager', 'member'] as const).map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => field.onChange(role)}
                      className={cn(
                        'flex h-full flex-col rounded-xl border p-3 text-left transition-colors',
                        field.value === role
                          ? 'border-primary bg-primary/10'
                          : 'border-white/10 bg-white/5 hover:bg-white/[0.08]',
                      )}
                    >
                      <p className="text-sm font-semibold capitalize">{role}</p>
                      <p className="text-muted-foreground mt-0.5 text-xs leading-tight">
                        {t(
                          `organiser.collaborators.role${role.charAt(0).toUpperCase() + role.slice(1)}Desc`,
                        )}
                      </p>
                    </button>
                  ))}
                </div>
              </FormControl>
              <p className="text-muted-foreground mt-2 flex items-center gap-1.5 text-xs">
                <Info className="h-3 w-3 shrink-0 opacity-60" />
                {t('organiser.collaborators.roleValidationNote')}
              </p>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Button type="submit" isLoading={invite.isPending}>
            {t('organiser.collaborators.inviteButton')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
