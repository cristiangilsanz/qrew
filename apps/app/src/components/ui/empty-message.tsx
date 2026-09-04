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
  // with an action the note carries a call, so it sits in the middle of the page
  // rather than clinging to the header with an empty stretch below it
  return (
    <div className="flex min-h-[55vh] flex-col items-center justify-center gap-4 text-center">
      <p className="text-muted-foreground text-sm">{children}</p>
      {action}
    </div>
  )
}
