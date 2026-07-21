import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

import { useProfile } from '../hooks/useProfile'

const kycColors: Record<string, string> = {
  approved: 'bg-green-100 text-green-800',
  pending: 'bg-yellow-100 text-yellow-800',
  rejected: 'bg-red-100 text-red-800',
  not_submitted: 'bg-gray-100 text-gray-600',
}

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

  const kycKey = profile.kyc_status as keyof typeof kycColors
  const badgeClass = kycColors[kycKey] ?? kycColors.not_submitted

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
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold tracking-wide uppercase ${badgeClass}`}
          >
            {t(`profile.kycStatus.${profile.kyc_status}`)}
          </span>
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
