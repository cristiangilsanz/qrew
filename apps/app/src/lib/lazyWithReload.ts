// loads a lazy chunk and recovers when a deploy has already replaced it
/* eslint-disable @typescript-eslint/no-explicit-any */
import { type ComponentType, lazy } from 'react'

const RELOAD_KEY = 'qrew:chunk-reload'

// reloads the page once so a stale bundle picks up the chunks that exist now
export function lazyWithReload<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
) {
  return lazy<T>(() =>
    factory()
      .then((loaded) => {
        sessionStorage.removeItem(RELOAD_KEY)
        return loaded
      })
      .catch((error: unknown) => {
        if (sessionStorage.getItem(RELOAD_KEY)) throw error
        sessionStorage.setItem(RELOAD_KEY, '1')
        window.location.reload()
        return new Promise<{ default: T }>(() => {})
      }),
  )
}
