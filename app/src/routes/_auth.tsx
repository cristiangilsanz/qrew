import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth')({
  beforeLoad: () => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/events' })
    }
  },
  component: AuthLayout,
})

function AuthLayout() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-background p-4">
      <Outlet />
    </div>
  )
}
