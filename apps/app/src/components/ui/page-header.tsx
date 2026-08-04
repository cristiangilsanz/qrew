import { type ReactNode } from 'react'

import { BackButton } from './back-button'

interface PageHeaderProps {
  title: string
  backTo?: string
  backParams?: Record<string, string>
  onBack?: () => void
  children?: ReactNode
}

export function PageHeader({ title, backTo, backParams, onBack, children }: PageHeaderProps) {
  return (
    <div className="flex items-center gap-3 px-4 pt-4 pb-2">
      {backTo ? (
        <BackButton to={backTo} params={backParams} />
      ) : onBack ? (
        <BackButton onClick={onBack} />
      ) : null}
      <h1 className="flex-1 text-2xl font-semibold">{title}</h1>
      {children}
    </div>
  )
}
