// implements router
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render, type RenderResult } from '@testing-library/react'

import { routeTree } from '@/routeTree.gen'

export interface RenderRouteResult extends RenderResult {
  router: ReturnType<typeof createTestRouter>
  queryClient: QueryClient
}

// implements create test router
function createTestRouter(path: string, queryClient: QueryClient) {
  return createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
    context: { queryClient },
    defaultPendingMinMs: 0,
  })
}

// implements render route
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

// implements current path
export function currentPath(router: RenderRouteResult['router']): string {
  return router.state.location.pathname
}

const SAMPLE_PARAM = 'fixture-id'

// the screens a visitor reaches without a session, which the tree cannot tell apart
export const AUTH_ONLY = [
  '/login',
  '/register',
  '/setup',
  '/verify-email',
  '/verify-totp',
  '/forgot-password',
  '/reset-password',
  '/confirm-email-change',
]

// lists every path the generated tree declares, so no screen can be added without
// a smoke test noticing, with each parameter filled by a stand in identifier
export function declaredPaths(options?: { under?: string; exclude?: string[] }): string[] {
  const router = createRouter({ routeTree, history: createMemoryHistory() })
  const exclude = new Set(options?.exclude ?? [])
  const paths = Object.values(router.routesById)
    .map((route) => route.fullPath as string)
    .filter((path) => path && !path.endsWith('/_app') && !path.endsWith('/_auth'))
    .map((path) => (path.length > 1 ? path.replace(/\/$/, '') : path))
    .filter((path) => !path.includes('$') || !path.endsWith('$'))
    .map((path) => path.replace(/\$[A-Za-z]+/g, SAMPLE_PARAM))
    .filter((path) => !exclude.has(path))
  const under = options?.under
  const wanted = under
    ? paths.filter((path) => path === under || path.startsWith(`${under}/`))
    : paths
  return [...new Set(wanted)].sort()
}
