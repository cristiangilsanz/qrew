import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { ShieldCheck } from 'lucide-react'
import { type KeyboardEvent, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { totpApi } from '@/features/auth/api'
import { AuthLayout } from '@/features/auth/components/AuthLayout'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

export const Route = createFileRoute('/_auth/verify-totp')({
  component: VerifyTotpPage,
})

const DIGITS = 6

function VerifyTotpPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const totpToken = useAuthStore((s) => s.totpToken)
  const setTokens = useAuthStore((s) => s.setTokens)
  const clearTotpPending = useAuthStore((s) => s.clearTotpPending)
  const [digits, setDigits] = useState<string[]>(Array(DIGITS).fill(''))
  const [isLoading, setIsLoading] = useState(false)
  const [hasError, setHasError] = useState(false)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    inputRefs.current[0]?.focus()
  }, [])

  const submit = async (code: string) => {
    if (!totpToken) { void navigate({ to: '/login' }); return }
    setIsLoading(true)
    setHasError(false)
    try {
      const data = await totpApi.verify(totpToken, code)
      setTokens(data.access_token, data.refresh_token)
      clearTotpPending()
      void navigate({ to: '/home' })
    } catch {
      toast.error(t('auth.totp.invalidCode'))
      setHasError(true)
      setDigits(Array(DIGITS).fill(''))
      setTimeout(() => inputRefs.current[0]?.focus(), 0)
    } finally {
      setIsLoading(false)
    }
  }

  const handleChange = (index: number, value: string) => {
    // Handle paste of full code into any cell
    const pasted = value.replace(/\D/g, '').slice(0, DIGITS)
    if (pasted.length > 1) {
      const next = [...Array(DIGITS).fill('')].map((_, i) => pasted[i] ?? '')
      setDigits(next)
      setHasError(false)
      const focusIdx = Math.min(pasted.length, DIGITS - 1)
      inputRefs.current[focusIdx]?.focus()
      if (pasted.length === DIGITS) void submit(pasted)
      return
    }

    const digit = value.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[index] = digit
    setDigits(next)
    setHasError(false)

    if (digit && index < DIGITS - 1) {
      inputRefs.current[index + 1]?.focus()
    }

    if (digit && index === DIGITS - 1) {
      const code = next.join('')
      if (code.length === DIGITS) void submit(code)
    }
  }

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (digits[index]) {
        const next = [...digits]
        next[index] = ''
        setDigits(next)
        setHasError(false)
      } else if (index > 0) {
        inputRefs.current[index - 1]?.focus()
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus()
    } else if (e.key === 'ArrowRight' && index < DIGITS - 1) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  const code = digits.join('')

  return (
    <AuthLayout title={t('auth.totp.title')} subtitle={t('auth.totp.subtitle')}>
      <div className="space-y-6">
        <div className="flex justify-center gap-3">
          {digits.map((digit, i) => (
            <input
              key={i}
              ref={(el) => { inputRefs.current[i] = el }}
              type="text"
              inputMode="numeric"
              autoComplete={i === 0 ? 'one-time-code' : 'off'}
              maxLength={DIGITS}
              value={digit}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              onFocus={(e) => e.target.select()}
              className={cn(
                'h-14 w-11 rounded-xl border bg-white/5 text-center text-xl font-bold text-white caret-transparent transition-all focus:outline-none focus:ring-2',
                hasError
                  ? 'border-red-500/60 focus:ring-red-500/40'
                  : digit
                    ? 'border-primary/60 focus:ring-primary/40'
                    : 'border-white/15 focus:ring-white/20',
              )}
            />
          ))}
        </div>

        {hasError && (
          <p className="text-center text-sm text-red-400">{t('auth.totp.invalidCode')}</p>
        )}

        <Button
          onClick={() => { if (code.length === DIGITS) void submit(code) }}
          disabled={code.length < DIGITS || isLoading}
          className="w-full rounded-full"
        >
          <ShieldCheck className="mr-2 h-4 w-4" />
          {t('auth.totp.verify')}
        </Button>
      </div>
    </AuthLayout>
  )
}
