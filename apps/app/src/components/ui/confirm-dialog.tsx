// implements confirm dialog
import { AnimatePresence, motion } from 'framer-motion'
import { type LucideIcon, Trash2 } from 'lucide-react'

export type ConfirmTone = 'default' | 'destructive' | 'warning'

const TONES: Record<
  ConfirmTone,
  { border: string; bubble: string; accent: string; button: string }
> = {
  default: {
    border: 'border-white/10',
    bubble: 'bg-white/10',
    accent: 'text-white',
    button: 'bg-primary',
  },
  destructive: {
    border: 'border-red-500/20',
    bubble: 'bg-red-500/10',
    accent: 'text-red-400',
    button: 'bg-red-500',
  },
  warning: {
    border: 'border-primary/30',
    bubble: 'bg-primary/10',
    accent: 'text-primary',
    button: 'bg-primary',
  },
}

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  note?: string
  confirmLabel: string
  cancelLabel?: string
  onConfirm: () => void
  isLoading?: boolean
  tone?: ConfirmTone
  icon?: LucideIcon
}

// renders the confirm dialog component
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  note,
  confirmLabel,
  cancelLabel = 'Go Back',
  onConfirm,
  isLoading = false,
  tone = 'default',
  icon: Icon = Trash2,
}: ConfirmDialogProps) {
  const palette = TONES[tone]

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[200] flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
          onClick={(e) => e.target === e.currentTarget && onOpenChange(false)}
        >
          <motion.div
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className={`w-full max-w-sm rounded-2xl border bg-[#111] p-6 ${palette.border}`}
          >
            <div className="mb-4 flex items-center gap-3">
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${palette.bubble}`}
              >
                <Icon className={`h-5 w-5 ${palette.accent}`} />
              </div>
              <h3 className={`text-base font-semibold ${palette.accent}`}>{title}</h3>
            </div>

            {description && (
              <p className={`text-muted-foreground text-sm ${note ? 'mb-2' : 'mb-5'}`}>
                {description}
              </p>
            )}
            {note && <p className="text-muted-foreground mb-5 text-sm">{note}</p>}

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
                className="flex h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-black disabled:opacity-50"
              >
                {cancelLabel}
              </button>
              <button
                type="button"
                onClick={onConfirm}
                disabled={isLoading}
                className={`flex h-10 min-w-[112px] items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold text-white disabled:opacity-50 ${palette.button}`}
              >
                <Icon className="h-3.5 w-3.5" />
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
