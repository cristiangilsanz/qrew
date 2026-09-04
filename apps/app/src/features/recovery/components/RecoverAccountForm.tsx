// renders the device recovery form component
import { useNavigate } from '@tanstack/react-router'
import { FileText, Info, KeyRound, Upload } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { Button } from '@/components/ui/button'
import { useProfile } from '@/features/profile/hooks/useProfile'
import { useAuthStore } from '@/store/auth'

import { useRecoverAccount } from '../hooks/useRecoverAccount'

// renders the device recovery form component
export function RecoverAccountForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: profile } = useProfile()
  const clearSession = useAuthStore((s) => s.clearSession)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // the preview holds an object url, which the browser only frees on request
  useEffect(() => {
    if (!file || !file.type.startsWith('image/')) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  // recovery replaces the key and revokes every device, so the session it ran
  // under is gone by the time it returns and the holder signs in afresh
  const recover = useRecoverAccount(() => {
    clearSession()
    void navigate({ to: '/login' })
  })

  // handles handle file change
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
  }

  // handles handle submit
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!profile?.email || !file) return
    recover.mutate({ email: profile.email, file })
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/profile/security" />
      <div>
        <h1 className="text-2xl font-semibold">{t('recovery.title')}</h1>
        <p className="text-muted-foreground mt-2 text-sm">{t('recovery.subtitle')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center gap-3 overflow-hidden rounded-xl border border-dashed border-white/20 px-4 py-6 text-sm transition-colors hover:bg-white/[0.04]"
        >
          {preview ? (
            <img
              src={preview}
              alt={file?.name ?? ''}
              className="max-h-56 w-full rounded-lg object-contain"
            />
          ) : file ? (
            <FileText className="text-muted-foreground h-8 w-8" />
          ) : (
            <Upload className="text-muted-foreground h-5 w-5" />
          )}
          <span className="text-muted-foreground max-w-full truncate">
            {file ? file.name : t('recovery.pickDocument')}
          </span>
          {file && <span className="text-xs text-white/40">{t('recovery.changeDocument')}</span>}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        <p className="text-muted-foreground flex items-start gap-1.5 text-xs">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-60" />
          <span>{t('recovery.note')}</span>
        </p>

        <Button
          type="submit"
          className="w-full rounded-full"
          disabled={!file}
          isLoading={recover.isPending}
        >
          <KeyRound className="mr-2 h-4 w-4" />
          {t('recovery.submit')}
        </Button>
      </form>
    </div>
  )
}
