import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusChip } from '@/components/ui/status-chip'

import { useProfile } from '../hooks/useProfile'

export function ProfileCard() {
  const { t, i18n } = useTranslation()
  const { data: profile, isLoading } = useProfile()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="flex justify-between">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-32" />
            </div>
          ))}
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
          <StatusChip
            label={t(`profile.kycStatus.${profile.kyc_status}`)}
            variant={profile.kyc_status}
          />
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
