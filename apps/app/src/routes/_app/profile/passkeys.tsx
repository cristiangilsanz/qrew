import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { PasskeyList } from '@/features/passkeys/components/PasskeyList'

export const Route = createFileRoute('/_app/profile/passkeys')({
  component: PasskeysPage,
})

function PasskeysPage() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-lg p-6">
      <h1 className="mb-6 text-2xl font-semibold">{t('passkeys.title')}</h1>
      <PasskeyList />
    </div>
  )
}
