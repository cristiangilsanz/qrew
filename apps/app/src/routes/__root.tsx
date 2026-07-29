import type { QueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router'
import { useEffect } from 'react'
import { Toaster } from 'sonner'

import { hapticLight } from '@/lib/haptics'

interface RouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Root,
})

function Root() {
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if ((e.target as Element).closest('button, a[role="button"], [data-haptic]')) {
        void hapticLight()
      }
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [])

  return (
    <div className="bg-background text-foreground min-h-screen">
      <div className="relative mx-auto min-h-screen max-w-[430px]">
        <Outlet />
      </div>
      <Toaster
        richColors
        theme="dark"
        position="top-center"
        toastOptions={{ classNames: { title: 'text-center w-full' } }}
      />
    </div>
  )
}
