import { Preferences } from '@capacitor/preferences'

export const storage = {
  get: (key: string) => Preferences.get({ key }).then((r) => r.value),
  set: (key: string, value: string) => Preferences.set({ key, value }),
  remove: (key: string) => Preferences.remove({ key }),
  clear: () => Preferences.clear(),
}
