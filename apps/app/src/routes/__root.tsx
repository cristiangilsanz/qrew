import type { QueryClient } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { Toaster } from 'sonner'

interface RouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Root,
})

function Root() {
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
      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools />
          <ReactQueryDevtools />
        </>
      )}
    </div>
  )
}
