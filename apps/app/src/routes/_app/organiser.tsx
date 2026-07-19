import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { profileApi } from '@/features/profile/api'

export const Route = createFileRoute('/_app/organiser')({
  beforeLoad: async () => {
    const profile = await profileApi.getMe()
    if (!profile.is_admin) {
      throw redirect({ to: '/home' })
    }
  },
  component: () => <Outlet />,
})
