import './styles/globals.css'
import './i18n'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { routeTree } from './routeTree.gen'
import { useAuthStore } from './store/auth'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0,
      gcTime: 0,
      retry: 1,
    },
  },
})

const router = createRouter({
  routeTree,
  context: { queryClient },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const mount = () => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </StrictMode>,
  )
}

if (useAuthStore.persist.hasHydrated()) {
  mount()
} else {
  useAuthStore.persist.onFinishHydration(mount)
}
