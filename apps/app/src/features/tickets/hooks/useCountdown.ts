import { useEffect, useState } from 'react'

function getSecondsUntil(expiresAt: string): number {
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000))
}

export function useCountdown(expiresAt: string | undefined): number {
  const [remaining, setRemaining] = useState(0)

  useEffect(() => {
    if (!expiresAt) {
      setRemaining(0)
      return
    }
    setRemaining(getSecondsUntil(expiresAt))
    const id = setInterval(() => {
      const r = getSecondsUntil(expiresAt)
      setRemaining(r)
      if (r <= 0) clearInterval(id)
    }, 1000)
    return () => clearInterval(id)
  }, [expiresAt])

  return remaining
}
