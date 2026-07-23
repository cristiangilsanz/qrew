import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { Info } from 'lucide-react'
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
import { Input } from '@/components/ui/input'
import { profileApi } from '@/features/profile/api'
import { cn } from '@/lib/utils'

import { useInviteMember } from '../hooks/useInviteMember'

const schema = z.object({
  user_id: z.string().uuid(),
  role: z.enum(['member', 'manager']),
})

type Values = z.infer<typeof schema>

interface Props {
  orgId: string
  existingMemberIds?: string[]
  onSuccess?: () => void
}

export function InviteMemberForm({ orgId, existingMemberIds = [], onSuccess }: Props) {
  const { t } = useTranslation()
  const [searchQ, setSearchQ] = useState('')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch all users once on mount; client-side filter for instant response
  const { data: allUsers = [] } = useQuery({
    queryKey: ['user-search-all'],
    queryFn: () => profileApi.searchUsers(''),
    staleTime: 60_000,
  })

  const filtered = allUsers
    .filter((u) => !existingMemberIds.includes(u.id))
    .filter((u) => {
      if (!searchQ.trim()) return true
      const q = searchQ.toLowerCase()
      return u.email.toLowerCase().includes(q) || u.full_name.toLowerCase().includes(q)
    })

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { user_id: '', role: 'member' },
  })

  const invite = useInviteMember(orgId)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

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
            onSuccess: () => {
              form.reset()
              setSearchQ('')
              onSuccess?.()
            },
          })
        })}
        className="w-full space-y-4"
      >
        {/* Hidden user_id field — value set when a suggestion is selected */}
        <input type="hidden" {...form.register('user_id')} />

        <FormItem>
          <FormLabel>{t('organiser.members.emailLabel')}</FormLabel>
          <div ref={containerRef} className="relative">
            <Input
              type="search"
              autoComplete="off"
              placeholder={t('organiser.members.emailPlaceholder')}
              value={searchQ}
              onChange={(e) => {
                setSearchQ(e.target.value)
                // Clear the stored user_id if the user edits the field manually
                form.setValue('user_id', '', { shouldValidate: false })
                setDropdownOpen(true)
              }}
              onFocus={() => setDropdownOpen(true)}
            />
            {dropdownOpen && filtered.length > 0 && (
              <ul className="absolute z-50 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-white/15 bg-black/95 shadow-xl backdrop-blur-md">
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
            <p className="text-destructive text-sm">{t('organiser.members.selectUser')}</p>
          )}
        </FormItem>
        <FormField
          control={form.control}
          name="role"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('organiser.members.roleLabel')}</FormLabel>
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
                      <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                        {t(
                          `organiser.members.role${role.charAt(0).toUpperCase() + role.slice(1)}Desc`,
                        )}
                      </p>
                    </button>
                  ))}
                </div>
              </FormControl>
              <p className="text-muted-foreground mt-2 flex items-center gap-1.5 text-xs">
                <Info className="h-3 w-3 shrink-0 opacity-60" />
                {t('organiser.members.roleValidationNote')}
              </p>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Button type="submit" isLoading={invite.isPending}>
            {t('organiser.members.inviteButton')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
