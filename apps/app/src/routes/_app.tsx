// implements app
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { BottomDock } from '@/components/layout/BottomDock'
import { RealtimeProvider } from '@/features/realtime/RealtimeProvider'
import { useAuthStore } from '@/store/auth'

// renders the app layout component
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

// renders the route error component
function RouteError({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'Something went wrong'
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="text-muted-foreground text-sm">{message}</p>
    </div>
  )
}

export const Route = createFileRoute('/_app')({
  // implements before load
  beforeLoad: () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
  errorComponent: RouteError,
})
