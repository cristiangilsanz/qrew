// renders the event skeletons component
import { Skeleton } from '@/components/ui/skeleton'

// renders the event card skeleton component
export function EventCardSkeleton() {
  return (
    <div className="bg-card border-border overflow-hidden rounded-xl border">
      <Skeleton className="h-44 w-full rounded-none" />
      <div className="space-y-2 p-4">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <div className="flex gap-3 pt-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
    </div>
  )
}

// renders the event detail skeleton component
export function EventDetailSkeleton() {
  return (
    <div className="pb-24">
      {/* Hero */}
      <Skeleton className="h-64 w-full rounded-none" />

      <div className="space-y-5 px-4 py-4">
        {/* Organiser + title */}
        <div className="space-y-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-3/4" />
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-5/6" />
          <Skeleton className="h-3.5 w-4/6" />
        </div>

        {/* Date */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 w-52" />
        </div>

        {/* Location */}
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-56" />
          </div>
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>

        {/* Sale countdown */}
        <div className="text-center">
          <Skeleton className="mx-auto mb-2 h-3 w-28" />
          <Skeleton className="mx-auto h-8 w-36" />
        </div>
      </div>
    </div>
  )
}

// renders the checkout skeleton component
export function CheckoutSkeleton() {
  return (
    <div className="mx-auto max-w-[430px] space-y-6 px-4 pt-5 pb-28">
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="space-y-1">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-5 w-32" />
        {[0, 1, 2].map((i) => (
          <div key={i} className="bg-card border-border space-y-2 rounded-xl border p-4">
            <Skeleton className="h-5 w-1/2" />
            <Skeleton className="h-3 w-full" />
            <div className="flex justify-between pt-1">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-12" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
