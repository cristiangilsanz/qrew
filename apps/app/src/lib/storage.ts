// implements storage
import { Preferences } from '@capacitor/preferences'
import type { StateStorage } from 'zustand/middleware'

export const storage = {
  // implements get
  get: (key: string) => Preferences.get({ key }).then((r) => r.value),
  // implements set
  set: (key: string, value: string) => Preferences.set({ key, value }),
  // implements remove
  remove: (key: string) => Preferences.remove({ key }),
  // implements clear
  clear: () => Preferences.clear(),
}

export const preferencesStorage: StateStorage = {
  // implements get item
  getItem: (name) => storage.get(name),
  // implements set item
  setItem: (name, value) => storage.set(name, value),
  // implements remove item
  removeItem: (name) => storage.remove(name),
}
