import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-white/10', className)} />
}

export {
  EventCardSkeleton,
  EventDetailSkeleton,
  CheckoutSkeleton,
} from '@/features/events/components/EventSkeletons'
export {
  ReservationRowSkeleton,
  TicketDetailSkeleton,
  ReservationSkeleton,
} from '@/features/tickets/components/TicketSkeletons'
export {
  EventManageSkeleton,
  OrgCardSkeleton,
  TicketTypeListSkeleton,
  FormPageSkeleton,
} from '@/features/organiser/components/OrganiserSkeletons'
export { WaitlistRowSkeleton } from '@/features/market/components/MarketSkeletons'
export { ProfileSkeleton, AccountSkeleton } from '@/features/profile/components/ProfileSkeletons'
export { OnboardingStepSkeleton } from '@/features/onboarding/components/OnboardingSkeletons'
