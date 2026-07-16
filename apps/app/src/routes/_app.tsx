import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { BottomDock } from '@/components/layout/BottomDock'
import { RealtimeProvider } from '@/features/realtime/RealtimeProvider'
import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_app')({
  beforeLoad: () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: () => (
    <RealtimeProvider>
      <div className="min-h-screen pb-20">
        <Outlet />
      </div>
      <BottomDock />
    </RealtimeProvider>
  ),
})
