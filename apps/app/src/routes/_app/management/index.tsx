// implements management
import { createFileRoute, Link } from '@tanstack/react-router'
import { Plus, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { FloatingActions } from '@/components/ui/floating-actions'
import { PageError } from '@/components/ui/page-error'
import { SEARCH_ICON_CLASS, SEARCH_INPUT_CLASS } from '@/components/ui/search-field'
import { OrgCardSkeleton } from '@/components/ui/skeleton'
import { OrgCard } from '@/features/organiser/components/OrgCard'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'

export const Route = createFileRoute('/_app/management/')({
  component: OrganiserPage,
})

// renders the organiser page component
function OrganiserPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  const { data, isLoading, isError, refetch } = useMyOrganisations()

  const myOrgs = data?.items ?? []
  const term = debouncedQuery.trim().toLowerCase()
  const isSearchMode = term.length > 0
  const displayOrgs = isSearchMode
    ? myOrgs.filter(
        (org) => org.name.toLowerCase().includes(term) || org.slug.toLowerCase().includes(term),
      )
    : myOrgs

  useEffect(() => {
    // implements timer
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  if (isError) return <PageError onRetry={() => void refetch()} />

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 pt-5 pb-28">
      <h1 className="text-2xl font-bold">{t('organiser.title')}</h1>

      <div className="relative">
        <Search className={SEARCH_ICON_CLASS} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') setDebouncedQuery(query)
          }}
          placeholder={t('organiser.search.placeholder')}
          className={SEARCH_INPUT_CLASS}
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery('')
              setDebouncedQuery('')
            }}
            className="text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {isLoading && (
        <div className="grid gap-4">
          {[0, 1].map((i) => (
            <OrgCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && !isError && displayOrgs.length === 0 && (
        <p className="text-muted-foreground py-8 text-center text-sm">
          {isSearchMode ? t('organiser.search.empty') : t('organiser.org.empty')}
        </p>
      )}

      <div className="space-y-3">
        {displayOrgs.map((org) => (
          <div
            key={org.id}
            className="overflow-hidden rounded-2xl border border-white/10 bg-white/5"
          >
            <OrgCard org={org} />
          </div>
        ))}
      </div>

      <FloatingActions>
        <Link
          to="/management/new"
          className="bg-primary hover:bg-primary/90 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        >
          <Plus className="h-5 w-5 shrink-0" />
          <span className="text-sm font-semibold">{t('organiser.org.create')}</span>
        </Link>
      </FloatingActions>
    </div>
  )
}
