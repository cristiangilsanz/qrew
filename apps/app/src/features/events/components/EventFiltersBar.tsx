import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

import { type EventFilters } from '../api'

interface Props {
  onFiltersChange: (filters: EventFilters) => void
}

export function EventFiltersBar({ onFiltersChange }: Props) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [city, setCity] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onFiltersChange({
      ...(q.trim() ? { q: q.trim() } : {}),
      ...(city.trim() ? { city: city.trim() } : {}),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t('events.searchPlaceholder')}
        className="flex-1"
      />
      <Input
        value={city}
        onChange={(e) => setCity(e.target.value)}
        placeholder={t('events.cityPlaceholder')}
        className="w-36"
      />
      <Button type="submit">{t('events.searchButton')}</Button>
    </form>
  )
}
