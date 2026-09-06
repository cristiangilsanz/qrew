// implements platform
import { Capacitor } from '@capacitor/core'

// implements is native
export const isNative = () => Capacitor.isNativePlatform()
