// implements recover device
import { createFileRoute } from '@tanstack/react-router'

import { RecoverAccountForm } from '@/features/recovery/components/RecoverAccountForm'

export const Route = createFileRoute('/_app/profile/recover-device')({
  component: RecoverAccountForm,
})
