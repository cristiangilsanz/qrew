import { Link, createFileRoute } from '@tanstack/react-router'
import { Plus, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { OrgCardSkeleton } from '@/components/ui/skeleton'
import { OrgCard } from '@/features/organiser/components/OrgCard'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'
import { useSearchOrgs } from '@/features/organiser/hooks/useSearchOrgs'

export const Route = createFileRoute('/_app/organiser/')({
  component: OrganiserPage,
})

function OrganiserPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  const { data, isLoading } = useMyOrganisations()
  const { data: searchResults, isFetching: isSearching } = useSearchOrgs(debouncedQuery)

  const myOrgs = data?.items ?? []
  const isSearchMode = debouncedQuery.trim().length > 0
  const displayOrgs = isSearchMode ? (searchResults ?? []) : myOrgs

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <h1 className="text-2xl font-semibold">{t('organiser.title')}</h1>

      {/* Search bar */}
      <div className="relative">
        <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') setDebouncedQuery(query)
          }}
          placeholder={t('organiser.search.placeholder')}
          className="border-input bg-background text-foreground placeholder:text-muted-foreground focus:ring-primary w-full rounded-xl border py-2.5 pr-9 pl-9 text-sm focus:ring-2 focus:outline-none"
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

      {(isLoading || isSearching) && (
        <div className="grid gap-4">
          {[0, 1].map((i) => (
            <OrgCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && !isSearching && displayOrgs.length === 0 && (
        <p className="text-muted-foreground py-8 text-center text-sm">
          {isSearchMode ? t('organiser.search.empty') : t('organiser.org.empty')}
        </p>
      )}

      <div className="space-y-3">
        {displayOrgs.map((org) => (
          <div key={org.id} className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
            <OrgCard org={org} />
          </div>
        ))}
      </div>

      {/* FAB */}
      <Link
        to="/organiser/new"
        className="bg-primary hover:bg-primary/90 fixed bottom-24 flex h-14 items-center gap-2 rounded-full px-5 text-white shadow-lg transition-colors"
        style={{ right: 'max(calc((100vw - 430px) / 2 + 1.5rem), 1.5rem)' }}
      >
        <Plus className="h-5 w-5 shrink-0" />
        <span className="text-sm font-semibold">{t('organiser.org.create')}</span>
      </Link>
    </div>
  )
}
