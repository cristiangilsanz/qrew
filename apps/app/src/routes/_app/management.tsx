// implements management
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { profileApi } from '@/features/profile/api'

export const Route = createFileRoute('/_app/management')({
  // implements before load
  beforeLoad: async () => {
    const profile = await profileApi.getMe()
    if (!profile.is_admin) {
      throw redirect({ to: '/home' })
    }
  },
  // implements component
  component: () => <Outlet />,
})
