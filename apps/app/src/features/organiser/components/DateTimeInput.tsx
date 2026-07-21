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
    'h-10 rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2 text-sm text-white/50 outline-none transition-all duration-150 focus:border-primary/50 focus:bg-white/8 focus:text-white [color-scheme:dark]'

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
