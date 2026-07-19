import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { BottomDock } from '@/components/layout/BottomDock'
import { RealtimeProvider } from '@/features/realtime/RealtimeProvider'
import { useAuthStore } from '@/store/auth'

function AppLayout() {
  return (
    <RealtimeProvider>
      <div className="relative min-h-screen">
        <div className="pb-20">
          <Outlet />
        </div>
      </div>
      <BottomDock />
    </RealtimeProvider>
  )
}

export const Route = createFileRoute('/_app')({
  beforeLoad: () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
})
