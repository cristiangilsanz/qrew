// reports whether the on screen keyboard is currently covering the view
import { Capacitor } from '@capacitor/core'
import { Keyboard } from '@capacitor/keyboard'
import { useEffect, useState } from 'react'

// tracks the keyboard so layout can react while the user types
export function useKeyboardOpen(): boolean {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return

    const shown = Keyboard.addListener('keyboardWillShow', () => setOpen(true))
    const hidden = Keyboard.addListener('keyboardWillHide', () => setOpen(false))

    return () => {
      void shown.then((l) => l.remove())
      void hidden.then((l) => l.remove())
    }
  }, [])

  return open
}
