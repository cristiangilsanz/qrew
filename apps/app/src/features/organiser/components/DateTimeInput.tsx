interface Props {
  value: string
  onChange: (value: string) => void
}

function toDatePart(iso: string): string {
  if (!iso) return ''
  return iso.slice(0, 10)
}

function toTimePart(iso: string): string {
  if (!iso) return ''
  // "2026-07-18T14:30" → "14:30"
  const t = iso.slice(11, 16)
  return t.length === 5 ? t : ''
}

function combine(date: string, time: string): string {
  if (!date) return ''
  return `${date}T${time || '00:00'}`
}

export function DateTimeInput({ value, onChange }: Props) {
  const datePart = toDatePart(value)
  const timePart = toTimePart(value)

  const base =
    'border-input bg-background text-foreground ring-offset-background focus-visible:ring-ring h-10 rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 [color-scheme:dark]'

  return (
    <div className="flex gap-2">
      <input
        type="date"
        value={datePart}
        onChange={(e) => onChange(combine(e.target.value, timePart))}
        className={`${base} min-w-0 flex-1`}
      />
      <input
        type="time"
        value={timePart}
        onChange={(e) => onChange(combine(datePart, e.target.value))}
        className={`${base} w-32 shrink-0`}
      />
    </div>
  )
}
