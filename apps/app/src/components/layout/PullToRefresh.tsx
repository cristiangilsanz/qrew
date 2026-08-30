// reloads the page's data when the user pulls down from the top
import { useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useRef, useState } from 'react'

const TRIGGER_DISTANCE = 72
const MAX_PULL = 110
const DAMPING = 0.5

interface Props {
  children: ReactNode
}

// wraps the page so a downward pull at the top refetches whatever it is showing
export function PullToRefresh({ children }: Props) {
  const queryClient = useQueryClient()
  const [distance, setDistance] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef<number | null>(null)
  const pulling = useRef(false)

  // refetches every query the current screen is subscribed to
  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await queryClient.refetchQueries({ type: 'active' })
    } finally {
      setRefreshing(false)
      setDistance(0)
    }
  }, [queryClient])

  useEffect(() => {
    // starts tracking only when the page is already scrolled to the very top
    const onTouchStart = (e: TouchEvent) => {
      if (refreshing || window.scrollY > 0 || document.body.classList.contains('scanner-active')) {
        startY.current = null
        return
      }
      startY.current = e.touches[0]?.clientY ?? null
      pulling.current = false
    }

    // follows the finger with damping so the gesture feels weighted
    const onTouchMove = (e: TouchEvent) => {
      if (startY.current === null || refreshing) return
      const current = e.touches[0]?.clientY ?? 0
      const delta = current - startY.current
      if (delta <= 0 || window.scrollY > 0) {
        if (!pulling.current) startY.current = null
        return
      }
      pulling.current = true
      if (e.cancelable) e.preventDefault()
      setDistance(Math.min(delta * DAMPING, MAX_PULL))
    }

    // a pull past the threshold reloads, anything shorter springs back
    const onTouchEnd = () => {
      if (startY.current === null) return
      startY.current = null
      if (!pulling.current) return
      pulling.current = false
      setDistance((d) => {
        if (d >= TRIGGER_DISTANCE) void refresh()
        return d >= TRIGGER_DISTANCE ? TRIGGER_DISTANCE : 0
      })
    }

    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: false })
    window.addEventListener('touchend', onTouchEnd, { passive: true })
    window.addEventListener('touchcancel', onTouchEnd, { passive: true })
    return () => {
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('touchend', onTouchEnd)
      window.removeEventListener('touchcancel', onTouchEnd)
    }
  }, [refresh, refreshing])

  const offset = refreshing ? TRIGGER_DISTANCE : distance
  const ready = distance >= TRIGGER_DISTANCE

  return (
    <>
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-30 flex justify-center"
        style={{ height: offset, opacity: offset > 0 ? 1 : 0 }}
      >
        <div className="flex h-full items-center">
          <Loader2
            className={`h-6 w-6 ${refreshing ? 'text-primary animate-spin' : ready ? 'text-primary' : 'text-muted-foreground'}`}
            style={{ transform: refreshing ? undefined : `rotate(${offset * 3}deg)` }}
          />
        </div>
      </div>
      {/* a transform makes this a containing block for fixed children, so only set one while pulling */}
      <div
        style={
          offset > 0
            ? {
                transform: `translateY(${offset}px)`,
                transition: startY.current === null ? 'transform 200ms ease-out' : undefined,
              }
            : undefined
        }
      >
        {children}
      </div>
    </>
  )
}
