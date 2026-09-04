// implements recover account
import { createFileRoute } from '@tanstack/react-router'

import { RecoverAccountForm } from '@/features/recovery/components/RecoverAccountForm'

export const Route = createFileRoute('/_auth/recover-account')({
  component: RecoverAccountForm,
})
