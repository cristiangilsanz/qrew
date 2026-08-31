// shows the one line a list falls back to when it has nothing to show
import { type ReactNode } from 'react'

interface EmptyMessageProps {
  children: ReactNode
  action?: ReactNode
}

// renders the same plain centred note wherever a list comes back empty
export function EmptyMessage({ children, action }: EmptyMessageProps) {
  if (!action) {
    return <p className="text-muted-foreground py-10 text-center text-sm">{children}</p>
  }
  return (
    <div className="flex flex-col items-center gap-4 py-10 text-center">
      <p className="text-muted-foreground text-sm">{children}</p>
      {action}
    </div>
  )
}
