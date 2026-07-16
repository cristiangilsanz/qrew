import { createFileRoute, redirect } from '@tanstack/react-router'

import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: '/home' })
    }
    throw redirect({ to: '/login' })
  },
})
