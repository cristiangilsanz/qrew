import { createFileRoute, Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChangeEmailForm } from '@/features/profile/components/ChangeEmailForm'
import { ChangePasswordForm } from '@/features/profile/components/ChangePasswordForm'
import { ChangePhoneForm } from '@/features/profile/components/ChangePhoneForm'
import { DeleteAccountDialog } from '@/features/profile/components/DeleteAccountDialog'
import { ProfileCard } from '@/features/profile/components/ProfileCard'
import { SessionList } from '@/features/profile/components/SessionList'

export const Route = createFileRoute('/_app/profile/')({
  component: ProfilePage,
})

function ProfilePage() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">{t('profile.title')}</h1>

      <ProfileCard />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('profile.sections.security')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-8">
          <ChangePasswordForm />
          <hr className="border-border" />
          <ChangeEmailForm />
          <hr className="border-border" />
          <ChangePhoneForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{t('profile.sections.passkeys')}</CardTitle>
            <Link to="/profile/passkeys" className="text-primary text-sm hover:underline">
              {t('profile.managePasskeys')}
            </Link>
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('profile.sections.sessions')}</CardTitle>
        </CardHeader>
        <CardContent>
          <SessionList />
        </CardContent>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive text-lg">
            {t('profile.sections.dangerZone')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DeleteAccountDialog />
        </CardContent>
      </Card>
    </div>
  )
}
