import { useState } from 'react'

import { cn } from '@/lib/utils'

import { Skeleton } from './skeleton'

interface Props {
  src: string
  alt?: string
  className?: string
  skeletonClassName?: string
}

export function ImageWithSkeleton({ src, alt, className, skeletonClassName }: Props) {
  const [loaded, setLoaded] = useState(false)

  return (
    <div className="relative h-full w-full">
      {!loaded && <Skeleton className={cn('absolute inset-0 rounded-none', skeletonClassName)} />}
      <img
        src={src}
        alt={alt}
        onLoad={() => setLoaded(true)}
        className={cn(className, !loaded && 'invisible')}
      />
    </div>
  )
}
