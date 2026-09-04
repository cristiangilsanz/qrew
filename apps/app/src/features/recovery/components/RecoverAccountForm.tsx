// renders the account recovery form component
import { Link, useNavigate } from '@tanstack/react-router'
import { KeyRound, Mail, Upload } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { AuthLayout } from '@/features/auth/components/AuthLayout'

import { useRecoverAccount } from '../hooks/useRecoverAccount'

// renders the account recovery form component
export function RecoverAccountForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const recover = useRecoverAccount(() => void navigate({ to: '/login' }))

  // handles handle file change
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
  }

  // handles handle submit
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!email || !file) return
    recover.mutate({ email, file })
  }

  return (
    <AuthLayout title={t('recovery.title')} subtitle={t('recovery.subtitle')}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <Mail className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            className="pl-9"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center gap-2 rounded-xl border border-dashed border-white/20 px-4 py-6 text-sm transition-colors hover:bg-white/[0.04]"
        >
          <Upload className="text-muted-foreground h-5 w-5" />
          <span className="text-muted-foreground">
            {file ? file.name : t('recovery.pickDocument')}
          </span>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        <Button
          type="submit"
          className="w-full rounded-full"
          disabled={!email || !file}
          isLoading={recover.isPending}
        >
          <KeyRound className="mr-2 h-4 w-4" />
          {t('recovery.submit')}
        </Button>
      </form>

      <p className="text-muted-foreground mt-4 text-center text-sm">
        <Link to="/login" className="text-primary font-medium hover:underline">
          {t('auth.login')}
        </Link>
      </p>
    </AuthLayout>
  )
}
