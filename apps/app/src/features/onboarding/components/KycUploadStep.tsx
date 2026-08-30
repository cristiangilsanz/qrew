// renders the kyc upload step component
import { ShieldCheck, Upload } from 'lucide-react'
import { type ChangeEvent, type FormEvent, type KeyboardEvent, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { DOCUMENT_TYPES, type DocumentType, isValidDocument } from '@/lib/documents'

import { type KycUploadResponse } from '../api'
import { useKycUpload } from '../hooks/useKycUpload'

interface Props {
  onSuccess: (data: KycUploadResponse) => void
}

// renders the kyc upload step component
export function KycUploadStep({ onSuccess }: Props) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState<DocumentType>('dni')
  const [documentNumber, setDocumentNumber] = useState('')
  const [preview, setPreview] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const upload = useKycUpload(onSuccess)

  // handles handle file change
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

  const documentValid = isValidDocument(documentNumber, documentType)

  // handles handle submit
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (file && documentValid) upload.mutate({ file, documentType, documentNumber })
  }

  // handles handle dropzone key down
  const handleDropzoneKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      inputRef.current?.click()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-muted-foreground text-sm">{t('onboarding.kyc.description')}</p>

      <div className="flex gap-2">
        <select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value as DocumentType)}
          className="border-input bg-background text-foreground shrink-0 rounded-xl border px-3 py-2.5 text-sm focus:outline-none"
        >
          {DOCUMENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`tickets.holders.documentType.${type}`)}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={documentNumber}
          onChange={(e) => setDocumentNumber(e.target.value)}
          placeholder={t(`tickets.holders.documentPlaceholder.${documentType}`)}
          className={`border-input bg-background text-foreground placeholder:text-muted-foreground w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none ${
            documentNumber && !documentValid ? 'border-red-500/60' : ''
          }`}
        />
      </div>
      {documentNumber && !documentValid && (
        <p className="px-1 text-xs text-red-400">{t(`tickets.holders.invalid.${documentType}`)}</p>
      )}

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

      <Button
        type="submit"
        className="w-full rounded-full"
        disabled={!file || !documentValid}
        isLoading={upload.isPending}
      >
        <ShieldCheck className="mr-2 h-4 w-4" />
        {t('onboarding.kyc.submit')}
      </Button>
    </form>
  )
}
