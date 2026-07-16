import { createFileRoute, Outlet, redirect, useRouterState } from '@tanstack/react-router'
import { AnimatePresence, motion } from 'framer-motion'
import { useRef } from 'react'

import { BottomDock } from '@/components/layout/BottomDock'
import { RealtimeProvider } from '@/features/realtime/RealtimeProvider'
import { useAuthStore } from '@/store/auth'

const TAB_ORDER: Record<string, number> = {
  '/home': 0,
  '/events': 1,
  '/tickets': 2,
  '/profile': 3,
}

function tabIndex(pathname: string) {
  for (const [prefix, idx] of Object.entries(TAB_ORDER)) {
    if (pathname.startsWith(prefix)) return idx
  }
  return -1
}

const variants = {
  enter: (dir: number) => ({ x: dir >= 0 ? '100%' : '-100%', opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir >= 0 ? '-100%' : '100%', opacity: 0 }),
}

function AppLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  const prevIndexRef = useRef(tabIndex(pathname))
  const directionRef = useRef(0)

  const currentIndex = tabIndex(pathname)

  // Only update direction when moving between top-level tabs
  if (currentIndex >= 0 && currentIndex !== prevIndexRef.current) {
    directionRef.current = currentIndex > prevIndexRef.current ? 1 : -1
    prevIndexRef.current = currentIndex
  }

  const direction = directionRef.current

  return (
    <RealtimeProvider>
      <div className="bg-background text-foreground relative mx-auto min-h-screen max-w-[430px] overflow-x-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={pathname}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            className="pb-20"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
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
