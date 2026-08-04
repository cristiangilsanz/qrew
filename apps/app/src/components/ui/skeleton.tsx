import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-white/10', className)} />
}

export {
  CheckoutSkeleton,
  EventCardSkeleton,
  EventDetailSkeleton,
} from '@/features/events/components/EventSkeletons'
export { WaitlistRowSkeleton } from '@/features/market/components/MarketSkeletons'
export { OnboardingStepSkeleton } from '@/features/onboarding/components/OnboardingSkeletons'
export {
  EventManageSkeleton,
  FormPageSkeleton,
  OrgCardSkeleton,
  TicketTypeListSkeleton,
} from '@/features/organiser/components/OrganiserSkeletons'
export { AccountSkeleton, ProfileSkeleton } from '@/features/profile/components/ProfileSkeletons'
export {
  ReservationRowSkeleton,
  ReservationSkeleton,
  TicketDetailSkeleton,
} from '@/features/tickets/components/TicketSkeletons'
