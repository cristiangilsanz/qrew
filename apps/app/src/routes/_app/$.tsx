import { createFileRoute, Link } from '@tanstack/react-router'
import { House } from 'lucide-react'

import notFoundImg from '@/assets/images/404.png'

export const Route = createFileRoute('/_app/$')({
  component: NotFoundPage,
})

function NotFoundPage() {
  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center gap-6 px-6">
      <img
        src={notFoundImg}
        alt="404 — page not found"
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
  )
}
