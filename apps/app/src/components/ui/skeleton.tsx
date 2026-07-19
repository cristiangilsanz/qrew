import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-white/10', className)} />
}

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

export function TicketCardSkeleton() {
  return (
    <div className="bg-card border-border overflow-hidden rounded-xl border">
      <Skeleton className="h-44 w-full rounded-none" />
      <div className="space-y-1.5 p-4">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-5 w-3/4" />
        <div className="flex gap-3 pt-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-28" />
        </div>
      </div>
    </div>
  )
}

export function TicketDetailSkeleton() {
  return (
    <div className="min-h-screen p-4 pb-24">
      <Skeleton className="mb-6 h-10 w-10 rounded-full" />
      <div className="mx-auto max-w-sm rounded-[2.5rem] bg-neutral-800 p-5">
        <div className="overflow-hidden rounded-3xl bg-white">
          <Skeleton className="h-48 w-full rounded-none bg-neutral-200" />
          <div className="space-y-2 px-5 pt-4 pb-4 text-center">
            <Skeleton className="mx-auto h-5 w-2/3 bg-neutral-200" />
            <Skeleton className="mx-auto h-4 w-1/2 bg-neutral-200" />
          </div>
          <div className="grid grid-cols-2 border-t border-gray-100">
            <div className="flex flex-col items-center gap-2 px-4 py-4">
              <Skeleton className="h-4 w-4 bg-neutral-200" />
              <Skeleton className="h-3 w-8 bg-neutral-200" />
              <Skeleton className="h-4 w-16 bg-neutral-200" />
            </div>
            <div className="flex flex-col items-center gap-2 border-l border-gray-100 px-4 py-4">
              <Skeleton className="h-4 w-4 bg-neutral-200" />
              <Skeleton className="h-3 w-8 bg-neutral-200" />
              <Skeleton className="h-4 w-12 bg-neutral-200" />
            </div>
          </div>
          <div className="space-y-2 bg-gray-50 px-5 py-3">
            <Skeleton className="h-3 w-full bg-neutral-200" />
            <Skeleton className="h-3 w-full bg-neutral-200" />
          </div>
        </div>
      </div>
    </div>
  )
}

export function EventDetailSkeleton() {
  return (
    <div className="pb-24">
      <Skeleton className="h-64 w-full rounded-none" />
      <div className="space-y-5 px-4 py-4">
        <div className="space-y-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-3/4" />
        </div>
        <Skeleton className="h-16 w-full" />
        <div className="flex gap-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
        <Skeleton className="h-12 w-full rounded-xl" />
      </div>
    </div>
  )
}

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

export function OrgCardSkeleton() {
  return (
    <div className="bg-card border-border space-y-2 rounded-xl border p-4">
      <Skeleton className="h-5 w-1/2" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  )
}

export function ReservationSkeleton() {
  return (
    <div className="mx-auto max-w-md space-y-6 p-6">
      <Skeleton className="h-10 w-10 rounded-full" />
      <Skeleton className="h-7 w-1/2" />
      <div className="bg-card border-border space-y-3 rounded-xl border p-4">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-12 w-full rounded-xl" />
    </div>
  )
}
