// implements empty state
import { type ReactNode } from 'react'

interface EmptyStateProps {
  image?: string
  imageAlt?: string
  title: string
  description?: string
  action?: ReactNode
}

// renders the empty state component
export function EmptyState({ image, imageAlt, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-6 px-6 text-center">
      {image && (
        <img src={image} alt={imageAlt ?? title} className="max-h-[35vh] w-auto object-contain" />
      )}
      <div className="flex flex-col gap-1">
        <p className="text-foreground font-medium">{title}</p>
        {description && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>
      {action}
    </div>
  )
}
