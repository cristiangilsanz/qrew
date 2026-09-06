// implements management
import { createFileRoute, Navigate, Outlet } from '@tanstack/react-router'

import { PageError } from '@/components/ui/page-error'
import { OrgCardSkeleton } from '@/components/ui/skeleton'
import { useMyOrganisations } from '@/features/organiser/hooks/useMyOrganisations'
import { useProfile } from '@/features/profile/hooks/useProfile'

export const Route = createFileRoute('/_app/management')({
  component: ManagementLayout,
})

// guards the management section from inside the app shell so the dock survives a failure
function ManagementLayout() {
  const profile = useProfile()
  const organisations = useMyOrganisations()

  if (profile.isError || organisations.isError) {
    return (
      <PageError
        onRetry={() => {
          void profile.refetch()
          void organisations.refetch()
        }}
      />
    )
  }

  if (profile.isLoading || organisations.isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 px-4 pt-5">
        <OrgCardSkeleton />
        <OrgCardSkeleton />
      </div>
    )
  }

  const belongsToAnOrganisation = (organisations.data?.items.length ?? 0) > 0
  if (profile.data?.is_admin !== true && !belongsToAnOrganisation) {
    return <Navigate to="/home" />
  }

  return <Outlet />
}
