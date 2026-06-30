import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_app')({
  beforeLoad: () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
})

function AppLayout() {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <main className="flex-1 pb-safe">
        <Outlet />
      </main>
    </div>
  )
}
