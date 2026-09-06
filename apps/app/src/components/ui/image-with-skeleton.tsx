// implements image with skeleton
import { useState } from 'react'

import { cn } from '@/lib/utils'

import { Skeleton } from './skeleton'

interface Props {
  src: string
  alt?: string
  className?: string
  skeletonClassName?: string
}

// renders the image with skeleton component
export function ImageWithSkeleton({ src, alt, className, skeletonClassName }: Props) {
  const [loaded, setLoaded] = useState(false)
  // implements settle
  const settle = () => setLoaded(true)

  return (
    <div className="relative h-full w-full">
      {!loaded && <Skeleton className={cn('absolute inset-0 rounded-none', skeletonClassName)} />}
      <img
        src={src}
        alt={alt}
        onLoad={settle}
        onError={settle}
        className={cn(className, !loaded && 'invisible')}
      />
    </div>
  )
}
