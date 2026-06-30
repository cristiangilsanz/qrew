import type { QueryClient } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { createRootRouteWithContext,Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'sonner'

interface RouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
})

function RootLayout() {
  return (
    <>
      <AnimatePresence mode="wait">
        <Outlet />
      </AnimatePresence>
      <Toaster richColors position="top-center" />
      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools />
          <ReactQueryDevtools />
        </>
      )}
    </>
  )
}
