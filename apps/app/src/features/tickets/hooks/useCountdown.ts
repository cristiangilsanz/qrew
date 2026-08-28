// provides use countdown
import { useEffect, useState } from 'react'

// implements get seconds until
function getSecondsUntil(expiresAt: string): number {
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000))
}

// provides use countdown
export function useCountdown(expiresAt: string | undefined): number {
  const [remaining, setRemaining] = useState(0)

  useEffect(() => {
    if (!expiresAt) {
      setRemaining(0)
      return
    }
    setRemaining(getSecondsUntil(expiresAt))
    // implements id
    const id = setInterval(() => {
      const r = getSecondsUntil(expiresAt)
      setRemaining(r)
      if (r <= 0) clearInterval(id)
    }, 1000)
    return () => clearInterval(id)
  }, [expiresAt])

  return remaining
}
