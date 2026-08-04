import { Skeleton } from '@/components/ui/skeleton'

export function ReservationRowSkeleton() {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-5 w-48" />
        <div className="flex items-center gap-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-32" />
        </div>
      </div>
      <div className="flex gap-3 overflow-hidden">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="bg-card border-border w-44 shrink-0 overflow-hidden rounded-xl border"
          >
            <Skeleton className="h-28 w-full rounded-none" />
            <div className="px-3 py-2.5">
              <div className="flex items-center justify-between gap-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-14 rounded-full" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function TicketDetailSkeleton() {
  return (
    <div className="min-h-screen px-4 pt-2 pb-24">
      <Skeleton className="mb-3 h-8 w-20 rounded-full" />
      <div className="mx-auto max-w-sm rounded-[2.5rem] bg-neutral-800 p-5">
        <div className="overflow-hidden rounded-3xl bg-white shadow-2xl">
          <Skeleton className="h-64 w-full rounded-none rounded-t-3xl bg-neutral-700" />
          <div className="space-y-1.5 px-5 pt-4 pb-3 text-center">
            <Skeleton className="mx-auto h-5 w-36 bg-neutral-200" />
            <Skeleton className="mx-auto h-3 w-20 bg-neutral-200" />
          </div>
          <div className="space-y-2 bg-white px-5 pt-3 pb-5">
            <div className="flex items-center justify-between">
              <Skeleton className="h-3 w-20 bg-neutral-200" />
              <Skeleton className="h-4 w-24 bg-neutral-200" />
            </div>
            <div className="flex items-center justify-between">
              <Skeleton className="h-3 w-16 bg-neutral-200" />
              <Skeleton className="h-4 w-20 bg-neutral-200" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-px">
            <div className="flex flex-col items-center gap-1.5 px-4 py-4">
              <Skeleton className="h-4 w-4 rounded bg-neutral-200" />
              <Skeleton className="h-3 w-8 bg-neutral-200" />
              <Skeleton className="h-4 w-24 bg-neutral-200" />
            </div>
            <div className="flex flex-col items-center gap-1.5 px-4 py-4">
              <Skeleton className="h-4 w-4 rounded bg-neutral-200" />
              <Skeleton className="h-3 w-8 bg-neutral-200" />
              <Skeleton className="h-4 w-14 bg-neutral-200" />
            </div>
          </div>
          <div className="mx-4 mt-4 mb-5 overflow-hidden rounded-2xl border border-gray-100">
            <div className="flex items-center justify-between bg-gray-50 px-4 py-3">
              <Skeleton className="h-3 w-14 bg-neutral-200" />
              <Skeleton className="h-4 w-4 rounded bg-neutral-200" />
            </div>
          </div>
          <div className="flex flex-col items-center justify-center gap-3 px-5 py-10">
            <Skeleton className="h-14 w-14 rounded-full bg-neutral-200" />
            <Skeleton className="h-3 w-40 bg-neutral-200" />
          </div>
        </div>
      </div>
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
