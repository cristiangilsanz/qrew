/* global google */
import { Loader } from '@googlemaps/js-api-loader'
import { zodResolver } from '@hookform/resolvers/zod'
import { MapPin, Plus } from 'lucide-react'
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
import { env } from '@/config/env'

import type { Venue } from '../api'
import { useCreateVenue } from '../hooks/useCreateVenue'

const schema = z.object({
  name: z.string().min(1),
  address_line: z.string().min(1),
  city: z.string().min(1),
  country: z.string().length(2),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  geofence_radius_m: z.coerce.number().int().min(50).max(5000).optional(),
  timezone: z.string().min(1),
  description: z.string().optional(),
})

type Values = z.infer<typeof schema>

const inputClass =
  'border-white/15 bg-white/5 placeholder:text-muted-foreground focus:border-primary/60 w-full rounded-xl border py-2.5 px-3 text-sm outline-none transition-colors text-white'

interface Props {
  onSuccess?: (venue: Venue) => void
}

export function CreateVenueForm({ onSuccess }: Props) {
  const { t } = useTranslation()
  const searchRef = useRef<HTMLInputElement>(null)
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null)
  const [mapsReady, setMapsReady] = useState(false)
  const [placeName, setPlaceName] = useState('')

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      address_line: '',
      city: '',
      country: '',
      latitude: 0,
      longitude: 0,
      geofence_radius_m: 200,
      timezone: '',
      description: '',
    },
  })

  const createVenue = useCreateVenue((venue: Venue) => {
    form.reset()
    setPlaceName('')
    onSuccess?.(venue)
  })

  // Load Google Maps Places library
  useEffect(() => {
    if (!env.GOOGLE_MAPS_API_KEY) return
    const loader = new Loader({
      apiKey: env.GOOGLE_MAPS_API_KEY,
      libraries: ['places'],
    })
    loader.load().then(() => setMapsReady(true)).catch(() => {/* silent — fallback to manual */})
  }, [])

  // Attach Autocomplete once maps is ready and input is mounted
  useEffect(() => {
    if (!mapsReady || !searchRef.current || autocompleteRef.current) return

    const ac = new google.maps.places.Autocomplete(searchRef.current, {
      types: ['establishment', 'geocode'],
      fields: ['name', 'address_components', 'geometry', 'formatted_address'],
    })
    autocompleteRef.current = ac

    ac.addListener('place_changed', () => {
      const place = ac.getPlace()
      if (!place.geometry?.location) return

      const lat = place.geometry.location.lat()
      const lng = place.geometry.location.lng()
      const comps = place.address_components ?? []

      const get = (type: string, short = false) =>
        comps.find((c) => c.types.includes(type))?.[short ? 'short_name' : 'long_name'] ?? ''

      const streetNum = get('street_number')
      const route = get('route')
      const addressLine = [streetNum, route].filter(Boolean).join(' ') || place.formatted_address || ''
      const city =
        get('locality') ||
        get('administrative_area_level_2') ||
        get('administrative_area_level_1')
      const country = get('country', true) // 2-char ISO

      form.setValue('name', place.name ?? '', { shouldValidate: true })
      form.setValue('address_line', addressLine, { shouldValidate: true })
      form.setValue('city', city, { shouldValidate: true })
      form.setValue('country', country, { shouldValidate: true })
      form.setValue('latitude', lat, { shouldValidate: true })
      form.setValue('longitude', lng, { shouldValidate: true })
      setPlaceName(place.name ?? place.formatted_address ?? '')

      // Auto-detect timezone via Google Timezone API
      if (env.GOOGLE_MAPS_API_KEY) {
        const ts = Math.floor(Date.now() / 1000)
        fetch(
          `https://maps.googleapis.com/maps/api/timezone/json?location=${lat},${lng}&timestamp=${ts}&key=${env.GOOGLE_MAPS_API_KEY}`,
        )
          .then((r) => r.json() as Promise<{ timeZoneId?: string }>)
          .then((data) => {
            if (data.timeZoneId) {
              form.setValue('timezone', data.timeZoneId, { shouldValidate: true })
            }
          })
          .catch(() => {/* ignore */})
      }
    })
  }, [mapsReady, form])

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((v) => createVenue.mutate(v))} className="space-y-4 px-1">

        {/* Places search */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium">{t('organiser.venues.searchLabel')}</label>
          <div className="relative">
            <MapPin className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
            <input
              ref={searchRef}
              type="search"
              autoComplete="off"
              placeholder={
                env.GOOGLE_MAPS_API_KEY
                  ? t('organiser.venues.searchPlaceholder')
                  : t('organiser.venues.searchUnavailable')
              }
              disabled={!env.GOOGLE_MAPS_API_KEY}
              className={`${inputClass} pl-9 disabled:cursor-not-allowed disabled:opacity-40`}
            />
          </div>
          {placeName && (
            <p className="text-primary flex items-center gap-1 text-xs">
              <MapPin className="h-3 w-3" />
              {placeName}
            </p>
          )}
        </div>

        <div className="border-t border-white/10 pt-4">
          <p className="text-muted-foreground mb-3 whitespace-pre-line text-xs">
            {t('organiser.venues.manualHint')}
          </p>

          <div className="space-y-3">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('organiser.venues.nameLabel')}</FormLabel>
                  <FormControl>
                    <Input className={inputClass} placeholder="Sala Razzmatazz" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="address_line"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('organiser.venues.addressLabel')}</FormLabel>
                  <FormControl>
                    <Input className={inputClass} placeholder="Carrer dels Almogàvers 122" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={form.control}
                name="city"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('organiser.venues.cityLabel')}</FormLabel>
                    <FormControl>
                      <Input className={inputClass} placeholder="Barcelona" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="country"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('organiser.venues.countryLabel')}</FormLabel>
                    <FormControl>
                      <Input className={inputClass} maxLength={2} placeholder="ES" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="latitude"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('organiser.venues.latLabel')}</FormLabel>
                    <FormControl>
                      <Input className={inputClass} type="number" step="any" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="longitude"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('organiser.venues.lngLabel')}</FormLabel>
                    <FormControl>
                      <Input className={inputClass} type="number" step="any" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="timezone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('organiser.venues.timezoneLabel')}</FormLabel>
                  <FormControl>
                    <Input className={inputClass} placeholder="Europe/Madrid" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="geofence_radius_m"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('organiser.venues.geofenceLabel')}</FormLabel>
                  <FormControl>
                    <Input className={inputClass} type="number" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button type="submit" isLoading={createVenue.isPending} className="rounded-full px-6">
            <Plus className="h-4 w-4" />
            {t('organiser.venues.newVenue')}
          </Button>
        </div>
      </form>
    </Form>
  )
}
