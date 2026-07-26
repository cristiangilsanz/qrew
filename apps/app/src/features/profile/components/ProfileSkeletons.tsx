import { Skeleton } from '@/components/ui/skeleton'

export function ProfileSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1].map((group) => (
        <div
          key={group}
          className={`overflow-hidden rounded-2xl border border-white/10 bg-white/5 ${group > 0 ? 'mt-4' : ''}`}
        >
          {[0, 1].map((row) => (
            <div key={row}>
              {row > 0 && <div className="mx-4 border-t border-white/10" />}
              <div className="flex items-center gap-3 px-4 py-4">
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-4 w-36" />
              </div>
            </div>
          ))}
        </div>
      ))}
      <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <div className="flex items-center gap-3 px-4 py-4">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="ml-auto h-8 w-20 rounded-full" />
        </div>
      </div>
      <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <div className="flex items-center gap-3 px-4 py-4">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 w-20" />
        </div>
      </div>
      <div className="mt-4 overflow-hidden rounded-2xl border border-red-500/20 bg-red-500/5">
        <div className="flex items-center gap-3 px-4 py-4">
          <Skeleton className="h-8 w-8 rounded-full bg-red-500/10" />
          <Skeleton className="h-4 w-32 bg-red-500/20" />
        </div>
      </div>
    </div>
  )
}

export function AccountSkeleton() {
  const rows = [
    { chip: false, value: true },
    { chip: false, value: true },
    { chip: true, value: false },
    { chip: true, value: true },
    { chip: true, value: true },
  ]
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
      {rows.map((row, i) => (
        <div key={i}>
          {i > 0 && <div className="mx-4 border-t border-white/10" />}
          <div className="flex items-center gap-3 px-4 py-4">
            <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
            <Skeleton className="h-4 w-10 shrink-0" />
            {row.chip && <Skeleton className="h-5 w-18 rounded-full" />}
            {row.value && <Skeleton className="ml-auto h-4 w-32" />}
          </div>
        </div>
      ))}
    </div>
  )
}
