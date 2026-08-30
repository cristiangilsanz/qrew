// implements app
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { useEffect } from 'react'

import { BottomDock } from '@/components/layout/BottomDock'
import { PageError } from '@/components/ui/page-error'
import { RealtimeProvider } from '@/features/realtime/RealtimeProvider'
import { useKeyboardOpen } from '@/hooks/useKeyboardOpen'
import { useAuthStore } from '@/store/auth'

// renders the app layout component
function AppLayout() {
  const keyboardOpen = useKeyboardOpen()

  useEffect(() => {
    document.body.classList.toggle('keyboard-open', keyboardOpen)
  }, [keyboardOpen])

  return (
    <RealtimeProvider>
      <div className="relative min-h-screen">
        <div className="min-h-[calc(100dvh+1.5rem)] pb-20">
          <Outlet />
        </div>
      </div>
      <BottomDock />
    </RealtimeProvider>
  )
}

// renders the route error component
function RouteError({ error }: { error: unknown }) {
  console.error('[route] render failed', error)
  return <PageError onRetry={() => window.location.reload()} />
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
