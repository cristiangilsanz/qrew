import { Button } from './button'
import { Dialog } from './dialog'

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
  cancelLabel = 'Cancel',
  onConfirm,
  isLoading = false,
  destructive = false,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onClose={() => onOpenChange(false)} title={title}>
      {description && <p className="text-muted-foreground mb-6 text-sm">{description}</p>}
      <div className="flex flex-col gap-3">
        <Button
          variant={destructive ? 'destructive' : 'default'}
          className="w-full rounded-full"
          isLoading={isLoading}
          onClick={onConfirm}
        >
          {confirmLabel}
        </Button>
        <Button
          variant="ghost"
          className="w-full rounded-full"
          onClick={() => onOpenChange(false)}
          disabled={isLoading}
        >
          {cancelLabel}
        </Button>
      </div>
    </Dialog>
  )
}
