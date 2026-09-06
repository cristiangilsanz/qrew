// implements list error
import { useTranslation } from 'react-i18next'

interface Props {
  onRetry?: () => void
}

// renders the list error component
export function ListError({ onRetry }: Props) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
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
