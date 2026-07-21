import { useQuery } from '@tanstack/react-query'
import { Calendar, ChevronDown, Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { type EventFilters, eventsApi } from '../api'

interface Props {
  onFiltersChange: (filters: EventFilters) => void
}

export function EventFiltersBar({ onFiltersChange }: Props) {
  const [q, setQ] = useState('')
  const [appliedQ, setAppliedQ] = useState('')
  const [selectedCities, setSelectedCities] = useState<string[]>([])
  const [fromDate, setFromDate] = useState('')
  const [cityOpen, setCityOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: allEvents } = useQuery({
    queryKey: ['events', {}],
    queryFn: () => eventsApi.list({ limit: 100 }),
    staleTime: 5 * 60 * 1000,
  })

  const availableCities = Array.from(
    new Set((allEvents?.items ?? []).map((e) => e.venue_city).filter((c): c is string => !!c)),
  ).sort()

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setCityOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [])

  useEffect(() => {
    onFiltersChange({
      ...(appliedQ.trim() ? { q: appliedQ.trim() } : {}),
      ...(selectedCities.length > 0 ? { cities: selectedCities } : {}),
      ...(fromDate ? { from: `${fromDate}T00:00:00`, to: `${fromDate}T23:59:59` } : {}),
    })
  }, [appliedQ, selectedCities, fromDate])

  const commitSearch = () => setAppliedQ(q)

  const toggleCity = (city: string) =>
    setSelectedCities((prev) =>
      prev.includes(city) ? prev.filter((c) => c !== city) : [...prev, city],
    )

  const hasFilters = !!appliedQ.trim() || selectedCities.length > 0 || !!fromDate

  const clearAll = () => {
    setQ('')
    setAppliedQ('')
    setSelectedCities([])
    setFromDate('')
  }

  return (
    <div className="space-y-3">
      {/* Search input */}
      <div className="relative">
        <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitSearch()
          }}
          placeholder="Search events…"
          className="border-input bg-background text-foreground placeholder:text-muted-foreground focus:ring-primary w-full rounded-xl border py-2.5 pr-9 pl-9 text-sm focus:ring-2 focus:outline-none"
        />
        {q && (
          <button
            type="button"
            onClick={() => {
              setQ('')
              setAppliedQ('')
            }}
            className="text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* City dropdown + Date picker row */}
      <div className="flex gap-2">
        {/* Multi-select city dropdown */}
        {availableCities.length > 0 && (
          <div ref={dropdownRef} className="relative flex-1">
            <button
              type="button"
              onClick={() => setCityOpen((o) => !o)}
              className={`border-input bg-background flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-sm transition-colors ${
                selectedCities.length > 0
                  ? 'border-primary text-foreground'
                  : 'text-muted-foreground'
              }`}
            >
              <span className="truncate">
                {selectedCities.length === 0
                  ? 'City'
                  : selectedCities.length === 1
                    ? selectedCities[0]
                    : `${selectedCities.length} cities`}
              </span>
              <ChevronDown
                className={`ml-2 h-4 w-4 shrink-0 transition-transform ${cityOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {cityOpen && (
              <div className="bg-card border-border absolute top-full left-0 z-50 mt-1 w-full rounded-xl border shadow-lg">
                <div className="max-h-52 overflow-y-auto py-1">
                  {availableCities.map((city) => {
                    const checked = selectedCities.includes(city)
                    return (
                      <button
                        key={city}
                        type="button"
                        onClick={() => toggleCity(city)}
                        className="hover:bg-muted flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm"
                      >
                        <span
                          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                            checked ? 'bg-primary border-primary' : 'border-input'
                          }`}
                        >
                          {checked && (
                            <svg viewBox="0 0 10 8" fill="none" className="h-2.5 w-2.5">
                              <path
                                d="M1 4l3 3 5-6"
                                stroke="white"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          )}
                        </span>
                        {city}
                      </button>
                    )
                  })}
                </div>
                {selectedCities.length > 0 && (
                  <div className="border-border border-t px-3 py-2">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedCities([])
                        setCityOpen(false)
                      }}
                      className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-2"
                    >
                      Clear cities
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Date picker */}
        <div className="relative">
          <Calendar className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className={`border-input bg-background text-foreground focus:ring-primary rounded-xl border py-2.5 pr-3 pl-9 text-sm focus:ring-2 focus:outline-none ${
              fromDate ? 'border-primary' : ''
            }`}
            style={{ colorScheme: 'dark' }}
          />
        </div>
      </div>

      {/* Active filters + clear all */}
      {hasFilters && (
        <div className="flex flex-wrap items-center gap-2">
          {appliedQ.trim() && (
            <span className="bg-primary/10 text-primary flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium">
              &quot;{appliedQ.trim()}&quot;
              <button
                type="button"
                onClick={() => {
                  setQ('')
                  setAppliedQ('')
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          {selectedCities.map((c) => (
            <span
              key={c}
              className="bg-primary/10 text-primary flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
            >
              {c}
              <button type="button" onClick={() => toggleCity(c)}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          {fromDate && (
            <span className="bg-primary/10 text-primary flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium">
              {new Date(fromDate).toLocaleDateString('en-GB', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
              })}
              <button type="button" onClick={() => setFromDate('')}>
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          <button
            type="button"
            onClick={clearAll}
            className="text-muted-foreground hover:text-foreground ml-auto text-xs underline underline-offset-2"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  )
}
