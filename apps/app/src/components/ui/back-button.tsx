// implements back button
import { useCanGoBack, useNavigate, useRouter } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { cn } from '@/lib/utils'

const circleClass =
  'flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white transition-colors hover:bg-primary/90'

interface Props {
  to?: string
  params?: Record<string, string>
  onClick?: () => void
  className?: string
}

// renders the back button component
export function BackButton({ className, to, params, onClick }: Props) {
  const router = useRouter()
  const canGoBack = useCanGoBack()
  const navigate = useNavigate()

  // returns to the previous step falling back to this screen's parent section
  const handleClick = () => {
    if (onClick) {
      onClick()
      return
    }
    if (canGoBack) {
      router.history.back()
      return
    }
    void navigate({ to: to ?? '/home', params } as never)
  }

  const placed = className?.includes('absolute') || className?.includes('fixed')

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(circleClass, !placed && 'sticky top-4 z-40', className)}
    >
      <ArrowLeft className="h-5 w-5" />
    </button>
  )
}
