import { ImagePlus, Loader2, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { apiClient } from '@/lib/api'
import { getEventImageUrl } from '@/lib/imageUrl'
import { cn } from '@/lib/utils'

interface Props {
  value: string | null
  onChange: (url: string | null) => void
}

async function uploadEventImage(file: File): Promise<string> {
  const { data: signed } = await apiClient.post<{
    key: string
    upload_url: string
    expires_at: number
  }>('/v1/uploads/sign', {
    kind: 'event_image',
    content_type: file.type,
    size_bytes: file.size,
  })

  const uploadRes = await fetch(signed.upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  })
  if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.status}`)

  return signed.key
}

export function EventImageUploader({ value, onChange }: Props) {
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Local blob URL shown immediately after selecting a file
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Revoke blob URL when component unmounts or preview changes
  useEffect(() => {
    return () => {
      if (previewUrl?.startsWith('blob:')) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith('image/')) {
        setError('Only image files are allowed')
        return
      }
      if (file.size > 5 * 1024 * 1024) {
        setError('Image must be under 5MB')
        return
      }
      setError(null)
      // Show local preview immediately
      const blob = URL.createObjectURL(file)
      setPreviewUrl(blob)
      setUploading(true)
      try {
        const key = await uploadEventImage(file)
        onChange(key)
      } catch {
        setError('Upload failed. Please try again.')
        setPreviewUrl(null)
        onChange(null)
      } finally {
        setUploading(false)
      }
    },
    [onChange],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) void handleFile(file)
    },
    [handleFile],
  )

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) void handleFile(file)
  }

  const handleRemove = () => {
    if (previewUrl?.startsWith('blob:')) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    onChange(null)
  }

  // Prefer local blob preview; fall back to server URL for existing saved keys
  const displayUrl = previewUrl ?? (value ? getEventImageUrl(value) : null)

  return (
    <div className="space-y-2">
      {displayUrl ? (
        <div className="relative overflow-hidden rounded-lg">
          <img src={displayUrl} alt="Event" className="h-40 w-full object-cover" />
          {uploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50">
              <Loader2 className="h-8 w-8 animate-spin text-white" />
            </div>
          )}
          {!uploading && (
            <button
              type="button"
              onClick={handleRemove}
              className="absolute top-2 right-2 rounded-full bg-black/60 p-1 transition-colors hover:bg-black/80"
            >
              <X className="h-4 w-4 text-white" />
            </button>
          )}
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          disabled={uploading}
          className={cn(
            'border-border flex h-40 w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed transition-colors',
            dragOver ? 'border-primary bg-primary/5' : 'hover:border-primary/50 hover:bg-muted/30',
          )}
        >
          <ImagePlus className="text-muted-foreground h-8 w-8" />
          <span className="text-muted-foreground text-sm">Drag & drop or click to upload</span>
          <span className="text-muted-foreground text-xs">JPG, PNG, WebP · max 5MB</span>
        </button>
      )}
      {error && <p className="text-destructive text-xs">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={onInputChange}
      />
    </div>
  )
}
