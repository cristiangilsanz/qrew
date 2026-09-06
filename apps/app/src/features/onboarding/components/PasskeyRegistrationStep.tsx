// renders the passkey registration step component
import { KeyRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import { useRegisterPasskey } from '../hooks/useRegisterPasskey'

interface Props {
  onSuccess: () => void
}

// renders the passkey registration step component
export function PasskeyRegistrationStep({ onSuccess }: Props) {
  const { t } = useTranslation()
  const register = useRegisterPasskey(onSuccess)

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center">
        <KeyRound className="text-primary mx-auto h-12 w-12" />
        <h2 className="text-lg font-semibold">{t('passkeys.register.title')}</h2>
        <p className="text-muted-foreground text-sm">{t('passkeys.register.description')}</p>
      </div>
      <Button
        className="w-full rounded-full"
        isLoading={register.isPending}
        onClick={() => register.mutate()}
      >
        <KeyRound className="mr-2 h-4 w-4" />
        {t('passkeys.register.submit')}
      </Button>
    </div>
  )
}
