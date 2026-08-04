import { Link } from '@tanstack/react-router'
import { House } from 'lucide-react'

import serverErrorImg from '@/assets/images/illustrations/server-error.webp'

export function ServerError() {
  return (
    <div className="bg-background text-foreground min-h-screen">
      <div className="relative mx-auto min-h-screen max-w-[430px]">
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-6">
          <img
            src={serverErrorImg}
            alt="Something went wrong"
            className="w-full max-w-xs object-contain"
          />
          <Link
            to="/home"
            className="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex h-12 items-center gap-2 rounded-full px-8 text-sm font-semibold transition-colors"
          >
            <House className="h-4 w-4" />
            Back To Home
          </Link>
        </div>
      </div>
    </div>
  )
}
