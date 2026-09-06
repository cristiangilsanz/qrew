// implements auth
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth')({
  // implements before load
  beforeLoad: () => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/home' })
    }
  },
  // implements component
  component: () => <Outlet />,
})
