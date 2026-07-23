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
          <div key={i} className="bg-card border-border w-44 shrink-0 overflow-hidden rounded-xl border">
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
      {/* Back button */}
      <Skeleton className="mb-3 h-8 w-20 rounded-full" />

      <div className="mx-auto max-w-sm rounded-[2.5rem] bg-neutral-800 p-5">
        <div className="overflow-hidden rounded-3xl bg-white shadow-2xl">

          {/* Event image */}
          <Skeleton className="h-64 w-full rounded-none rounded-t-3xl bg-neutral-700" />

          {/* Holder name + DNI */}
          <div className="px-5 pt-4 pb-3 text-center space-y-1.5">
            <Skeleton className="mx-auto h-5 w-36 bg-neutral-200" />
            <Skeleton className="mx-auto h-3 w-20 bg-neutral-200" />
          </div>

          {/* ID strip */}
          <div className="bg-white px-5 pt-3 pb-5 space-y-2">
            <div className="flex items-center justify-between">
              <Skeleton className="h-3 w-20 bg-neutral-200" />
              <Skeleton className="h-4 w-24 bg-neutral-200" />
            </div>
            <div className="flex items-center justify-between">
              <Skeleton className="h-3 w-16 bg-neutral-200" />
              <Skeleton className="h-4 w-20 bg-neutral-200" />
            </div>
          </div>

          {/* Date / Time grid */}
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

          {/* History expandable */}
          <div className="mx-4 mt-4 mb-5 overflow-hidden rounded-2xl border border-gray-100">
            <div className="flex items-center justify-between bg-gray-50 px-4 py-3">
              <Skeleton className="h-3 w-14 bg-neutral-200" />
              <Skeleton className="h-4 w-4 rounded bg-neutral-200" />
            </div>
          </div>

          {/* QR / state area */}
          <div className="flex flex-col items-center justify-center gap-3 px-5 py-10">
            <Skeleton className="h-14 w-14 rounded-full bg-neutral-200" />
            <Skeleton className="h-3 w-40 bg-neutral-200" />
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
        <Skeleton className="h-12 w-full" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-56" />
          </div>
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
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

export function AccountSkeleton() {
  // rows: [name, memberSince, kyc(chip), email(chip), phone(chip)]
  const rows = [
    { chip: false, value: true },
    { chip: false, value: true },
    { chip: true,  value: false },
    { chip: true,  value: true },
    { chip: true,  value: true },
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

export function OnboardingStepSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex flex-1 flex-col items-center gap-1">
            <Skeleton className="h-7 w-7 rounded-full" />
            <Skeleton className="h-3 w-12" />
          </div>
        ))}
      </div>
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-10 w-full rounded-xl" />
        <Skeleton className="h-10 w-full rounded-xl" />
        <Skeleton className="h-10 w-full rounded-full" />
      </div>
    </div>
  )
}

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

export function TicketTypeListSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1].map((i) => (
        <div key={i} className="flex overflow-hidden rounded-2xl bg-white/10">
          <div className="flex min-w-0 flex-1 items-center gap-2 py-6 pl-5 pr-3">
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
