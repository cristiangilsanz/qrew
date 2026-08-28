// implements haptics
import { Haptics, ImpactStyle } from '@capacitor/haptics'

// implements haptic light
export async function hapticLight() {
  await Haptics.impact({ style: ImpactStyle.Light }).catch(() => {})
}

// implements haptic medium
export async function hapticMedium() {
  await Haptics.impact({ style: ImpactStyle.Medium }).catch(() => {})
}

// implements haptic heavy
export async function hapticHeavy() {
  await Haptics.impact({ style: ImpactStyle.Heavy }).catch(() => {})
}
