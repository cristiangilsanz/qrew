import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusChip } from '@/components/ui/status-chip'

import { useProfile } from '../hooks/useProfile'

export function ProfileCard() {
  const { t, i18n } = useTranslation()
  const { data: profile, isLoading } = useProfile()

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex justify-center py-8">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
        </CardContent>
      </Card>
    )
  }

  if (!profile) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t('profile.sections.personal')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('auth.fullName')}</span>
          <span className="font-medium">{profile.full_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('auth.email')}</span>
          <span className="font-medium">{profile.email}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('auth.phoneNumber')}</span>
          <span className="font-medium">{profile.phone_number}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('profile.kycStatus.label')}</span>
          <StatusChip label={t(`profile.kycStatus.${profile.kyc_status}`)} variant={profile.kyc_status} />
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">
            {t('profile.memberSince', { date: '' }).trim()}
          </span>
          <span className="font-medium">
            {new Date(profile.created_at).toLocaleDateString(i18n.language)}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
