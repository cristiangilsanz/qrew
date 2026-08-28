// language to locale map for local date format
const LOCALE_MAP: Record<string, string> = {
  en: 'en-GB',
  es: 'es-ES',
}

// implements to locale
function toLocale(lang: string): string {
  return LOCALE_MAP[lang] ?? lang
}

// implements format date
export function formatDate(
  date: Date | string,
  lang: string,
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString(toLocale(lang), options)
}

// implements format date time
export function formatDateTime(
  date: Date | string,
  lang: string,
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleString(toLocale(lang), options)
}
