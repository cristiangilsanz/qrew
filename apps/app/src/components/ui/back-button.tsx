import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { cn } from '@/lib/utils'

const circleClass =
  'flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white transition-colors hover:bg-primary/90'

interface LinkProps {
  to: string
  params?: Record<string, string>
  onClick?: never
  className?: string
}

interface ButtonProps {
  onClick: () => void
  to?: never
  params?: never
  className?: string
}

type Props = LinkProps | ButtonProps

export function BackButton({ className, ...props }: Props) {
  if (props.to !== undefined) {
    return (
      <Link to={props.to} params={props.params} className={cn(circleClass, className)}>
        <ArrowLeft className="h-5 w-5" />
      </Link>
    )
  }
  return (
    <button type="button" onClick={props.onClick} className={cn(circleClass, className)}>
      <ArrowLeft className="h-5 w-5" />
    </button>
  )
}
