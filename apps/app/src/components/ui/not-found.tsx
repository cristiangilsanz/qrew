import { type ReactNode } from 'react'

interface Props {
  message: string
  action?: ReactNode
}

export function NotFound({ message, action }: Props) {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="text-muted-foreground text-sm">{message}</p>
      {action}
    </div>
  )
}
