import { Skeleton } from '@/components/ui/skeleton'

export function WaitlistRowSkeleton() {
  return (
    <div className="bg-card border-border overflow-hidden rounded-xl border">
      <Skeleton className="h-24 w-full rounded-none" />
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <div className="min-w-0 space-y-1.5">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-28" />
        </div>
        <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
      </div>
    </div>
  )
}
