// implements page error
import { useTranslation } from 'react-i18next'

interface Props {
  onRetry?: () => void
}

// renders the only thing a page shows when its data cannot be loaded
export function PageError({ onRetry }: Props) {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-[70dvh] flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-muted-foreground text-sm">{t('common.error')}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="border-border text-foreground hover:bg-muted h-9 rounded-full border px-5 text-sm font-medium transition-colors"
        >
          {t('common.retry')}
        </button>
      )}
    </div>
  )
}
