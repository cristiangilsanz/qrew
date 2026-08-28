// renders the organiser skeletons component
import { Skeleton } from '@/components/ui/skeleton'

// renders the event manage skeleton component
export function EventManageSkeleton() {
  return (
    <div className="pb-28">
      <Skeleton className="h-56 w-full rounded-none" />
      <div className="mx-auto max-w-2xl space-y-6 px-4 pt-4">
        <Skeleton className="h-7 w-48" />
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
          {[0, 1].map((row) => (
            <div key={row}>
              {row > 0 && <div className="mx-4 border-t border-white/10" />}
              <div className="flex items-center gap-3 px-4 py-4">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-56" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// renders the org card skeleton component
export function OrgCardSkeleton() {
  return (
    <div className="bg-card border-border overflow-hidden rounded-2xl border bg-white/5">
      <div className="flex items-center gap-3 px-4 py-4">
        <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-4 w-4 rounded" />
      </div>
    </div>
  )
}

// renders the ticket type list skeleton component
export function TicketTypeListSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1].map((i) => (
        <div key={i} className="flex overflow-hidden rounded-2xl bg-white/10">
          <div className="flex min-w-0 flex-1 items-center gap-2 py-6 pr-3 pl-5">
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-32 bg-white/20" />
              <Skeleton className="h-3 w-24 bg-white/20" />
            </div>
          </div>
          <div className="my-4 border-l border-dashed border-white/20" />
          <div className="flex w-20 shrink-0 flex-col items-center justify-center gap-1 px-2 py-6">
            <Skeleton className="h-4 w-12 bg-white/20" />
            <Skeleton className="h-3 w-8 bg-white/20" />
          </div>
        </div>
      ))}
    </div>
  )
}

// renders the form page skeleton component
export function FormPageSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="space-y-1.5">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-10 w-full rounded-xl" />
        </div>
      ))}
    </div>
  )
}
