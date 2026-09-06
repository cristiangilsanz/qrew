// implements reset password
import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'

import { ResetPasswordForm } from '@/features/auth/components/ResetPasswordForm'

export const Route = createFileRoute('/_auth/reset-password')({
  validateSearch: z.object({ token: z.string() }),
  // implements component
  component: function ResetPasswordRoute() {
    const { token } = Route.useSearch()
    return <ResetPasswordForm token={token} />
  },
})
