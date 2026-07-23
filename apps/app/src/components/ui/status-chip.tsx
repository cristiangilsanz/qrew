import { cn } from '@/lib/utils'

const variants: Record<string, string> = {
  // event status
  draft: 'bg-white/8 text-white/50 border border-white/10',
  published: 'bg-primary/15 text-primary border border-primary/30',
  cancelled: 'bg-red-500/15 text-red-400 border border-red-500/20',
  // ticket states
  reserved: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20',
  issued: 'bg-primary/15 text-primary border border-primary/30',
  scanning: 'bg-purple-500/15 text-purple-400 border border-purple-500/20',
  redeemed: 'bg-green-500/15 text-green-400 border border-green-500/20',
  expired: 'bg-white/8 text-white/40 border border-white/10',
  on_sale: 'bg-blue-500/15 text-blue-400 border border-blue-500/20',
  flagged: 'bg-amber-900/20 text-amber-900 border border-amber-900/30',
  // kyc status
  approved: 'bg-primary/15 text-primary border border-primary/30',
  pending: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20',
  rejected: 'bg-red-500/15 text-red-400 border border-red-500/20',
  not_submitted: 'bg-white/8 text-white/40 border border-white/10',
  // member roles
  owner: 'bg-primary/15 text-primary border border-primary/30',
  manager: 'bg-blue-500/15 text-blue-300 border border-blue-500/20',
  member: 'bg-white/8 text-white/50 border border-white/10',
}

interface Props {
  label: string
  variant?: string
  className?: string
}

export function StatusChip({ label, variant, className }: Props) {
  const key = variant ?? label.toLowerCase().replace(' ', '_')
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase',
        variants[key] ?? 'border border-white/10 bg-white/8 text-white/50',
        className,
      )}
    >
      {label}
    </span>
  )
}
