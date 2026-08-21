import { Preferences } from '@capacitor/preferences'
import type { StateStorage } from 'zustand/middleware'

export const storage = {
  get: (key: string) => Preferences.get({ key }).then((r) => r.value),
  set: (key: string, value: string) => Preferences.set({ key, value }),
  remove: (key: string) => Preferences.remove({ key }),
  clear: () => Preferences.clear(),
}

export const preferencesStorage: StateStorage = {
  getItem: (name) => storage.get(name),
  setItem: (name, value) => storage.set(name, value),
  removeItem: (name) => storage.remove(name),
}
