import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render, type RenderResult } from '@testing-library/react'

import { routeTree } from '@/routeTree.gen'

export interface RenderRouteResult extends RenderResult {
  router: ReturnType<typeof createTestRouter>
  queryClient: QueryClient
}

function createTestRouter(path: string, queryClient: QueryClient) {
  return createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
    context: { queryClient },
    defaultPendingMinMs: 0,
  })
}

export async function renderRoute(path: string): Promise<RenderRouteResult> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  })
  const router = createTestRouter(path, queryClient)
  await router.load()
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...utils, router, queryClient }
}

export function currentPath(router: RenderRouteResult['router']): string {
  return router.state.location.pathname
}
