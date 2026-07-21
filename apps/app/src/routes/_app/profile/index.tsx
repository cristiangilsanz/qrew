import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { ChevronRight, Globe, HelpCircle, Info, LogOut, Shield, User } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { DeleteAccountDialog } from '@/features/profile/components/DeleteAccountDialog'
import { useProfile } from '@/features/profile/hooks/useProfile'
import i18n from '@/i18n'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_app/profile/')({
  component: ProfilePage,
})

const SUPPORTED_LANGS = [
  { code: 'en', label: 'EN' },
  { code: 'es', label: 'ES' },
]

function ProfilePage() {
  const { t } = useTranslation()
  const { data: profile, isLoading } = useProfile()
  const clearSession = useAuthStore((s) => s.clearSession)
  const navigate = useNavigate()
  const [currentLang, setCurrentLang] = useState(i18n.language.split('-')[0])

  const changeLanguage = (lang: string) => {
    void i18n.changeLanguage(lang)
    localStorage.setItem('qrew_lang', lang)
    setCurrentLang(lang)
  }

  const handleLogout = () => {
    clearSession()
    void navigate({ to: '/login' })
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
      </div>
    )
  }

  if (!profile) return null

  return (
    <div className="min-h-screen px-4 pt-6 pb-28">
      <h1 className="mb-8 text-2xl font-bold">{t('profile.myProfile')}</h1>

      {/* Main sections */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <Link
          to="/profile/account"
          className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
            <User className="text-muted-foreground h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('profile.myAccount')}</span>
          <ChevronRight className="text-muted-foreground h-4 w-4" />
        </Link>

        <div className="mx-4 border-t border-white/10" />

        <Link
          to="/profile/security"
          className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
            <Shield className="text-muted-foreground h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('profile.privacySecurity')}</span>
          <ChevronRight className="text-muted-foreground h-4 w-4" />
        </Link>
      </div>

      {/* Help & About */}
      <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <Link
          to="/profile/help"
          className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
            <HelpCircle className="text-muted-foreground h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('profile.helpSupport')}</span>
          <ChevronRight className="text-muted-foreground h-4 w-4" />
        </Link>

        <div className="mx-4 border-t border-white/10" />

        <Link
          to="/profile/about"
          className="flex items-center gap-3 px-4 py-4 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
            <Info className="text-muted-foreground h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('profile.about.title')}</span>
          <ChevronRight className="text-muted-foreground h-4 w-4" />
        </Link>
      </div>

      {/* Language */}
      <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <div className="flex items-center gap-3 px-4 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
            <Globe className="text-muted-foreground h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('profile.language')}</span>
          <div className="flex items-center gap-1 rounded-full bg-white/10 p-1">
            {SUPPORTED_LANGS.map((lang) => (
              <button
                key={lang.code}
                onClick={() => changeLanguage(lang.code)}
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-semibold transition-colors',
                  currentLang === lang.code
                    ? 'bg-primary text-white'
                    : 'text-muted-foreground hover:text-white',
                )}
              >
                {lang.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Log out */}
      <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
            <LogOut className="text-muted-foreground h-4 w-4" />
          </div>
          <span className="flex-1 text-sm font-medium">{t('profile.logout')}</span>
        </button>
      </div>

      {/* Delete account */}
      <div className="mt-4 overflow-hidden rounded-2xl border border-red-500/20 bg-red-500/5">
        <DeleteAccountDialog />
      </div>
    </div>
  )
}
