import { X } from 'lucide-react'
import { type ReactNode, useEffect } from 'react'

import { cn } from '@/lib/utils'

interface DialogProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  className?: string
  size?: 'default' | 'lg'
}

export function Dialog({ open, onClose, title, children, className, size = 'default' }: DialogProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={cn(
          'bg-card relative z-10 w-full rounded-t-2xl p-5 shadow-xl sm:rounded-2xl',
          size === 'lg' ? 'max-w-2xl' : 'max-w-[430px]',
          className,
        )}
      >
        <div className="mb-4 flex items-center justify-between">
          {title && <h2 className="text-base font-semibold">{title}</h2>}
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground ml-auto transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className={cn('pb-safe overflow-y-auto', size === 'lg' ? 'max-h-[85vh]' : 'max-h-[80vh]')}>{children}</div>
      </div>
    </div>
  )
}
