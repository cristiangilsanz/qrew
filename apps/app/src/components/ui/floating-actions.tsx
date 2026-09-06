// anchors a page's floating actions so every screen puts them in the same place
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface Props {
  children: ReactNode
  className?: string
}

// pins the row just above the dock, aligned with the column the page content uses
export function FloatingActions({ children, className }: Props) {
  return (
    <div className="keyboard-hide fixed inset-x-0 bottom-24 z-40">
      <div
        className={cn(
          'mx-auto flex w-full max-w-[430px] items-center justify-end gap-3 px-4',
          className,
        )}
      >
        {children}
      </div>
    </div>
  )
}
