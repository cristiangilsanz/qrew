import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth')({
  beforeLoad: () => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/events' })
    }
  },
  component: () => <Outlet />,
})
