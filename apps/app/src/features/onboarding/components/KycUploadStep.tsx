import { Upload } from 'lucide-react'
import { type ChangeEvent, type FormEvent, type KeyboardEvent, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

import { type KycUploadResponse } from '../api'
import { useKycUpload } from '../hooks/useKycUpload'

interface Props {
  onSuccess: (data: KycUploadResponse) => void
}

export function KycUploadStep({ onSuccess }: Props) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const upload = useKycUpload(onSuccess)

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return
    setFile(selected)
    if (selected.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(selected))
    } else {
      setPreview(null)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (file) upload.mutate(file)
  }

  const handleDropzoneKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      inputRef.current?.click()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-muted-foreground text-sm">{t('onboarding.kyc.description')}</p>

      <div
        role="button"
        tabIndex={0}
        className="border-border hover:border-primary cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors"
        onClick={() => inputRef.current?.click()}
        onKeyDown={handleDropzoneKeyDown}
      >
        {preview ? (
          <img
            src={preview}
            alt="Document preview"
            className="mx-auto max-h-40 rounded object-contain"
          />
        ) : (
          <div className="space-y-2">
            <Upload className="text-muted-foreground mx-auto h-8 w-8" />
            <p className="text-muted-foreground text-sm">
              {file ? file.name : t('onboarding.kyc.dropzone')}
            </p>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      {file && !preview && <p className="text-muted-foreground truncate text-sm">{file.name}</p>}

      <Button type="submit" className="w-full" disabled={!file} isLoading={upload.isPending}>
        {t('onboarding.kyc.submit')}
      </Button>
    </form>
  )
}
