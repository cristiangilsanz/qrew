import { AnimatePresence, motion } from 'framer-motion'
import { Trash2 } from 'lucide-react'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  confirmLabel: string
  cancelLabel?: string
  onConfirm: () => void
  isLoading?: boolean
  destructive?: boolean
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = 'Go Back',
  onConfirm,
  isLoading = false,
  destructive = false,
}: ConfirmDialogProps) {
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
            className={`w-full max-w-sm rounded-2xl border p-6 ${
              destructive ? 'border-red-500/20 bg-[#111]' : 'border-white/10 bg-[#111]'
            }`}
          >
            <div className="mb-4 flex items-center gap-3">
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                  destructive ? 'bg-red-500/10' : 'bg-white/10'
                }`}
              >
                <Trash2 className={`h-5 w-5 ${destructive ? 'text-red-400' : 'text-white/70'}`} />
              </div>
              <h3
                className={`text-base font-semibold ${destructive ? 'text-red-400' : 'text-white'}`}
              >
                {title}
              </h3>
            </div>

            {description && <p className="text-muted-foreground mb-5 text-sm">{description}</p>}

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
                className={`flex h-10 min-w-[112px] items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold text-white disabled:opacity-50 ${
                  destructive ? 'bg-red-500' : 'bg-primary'
                }`}
              >
                <>
                  <Trash2 className="h-3.5 w-3.5" />
                  {confirmLabel}
                </>
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
