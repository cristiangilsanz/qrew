import { Haptics, ImpactStyle } from '@capacitor/haptics'

export async function hapticLight() {
  await Haptics.impact({ style: ImpactStyle.Light }).catch(() => {})
}

export async function hapticMedium() {
  await Haptics.impact({ style: ImpactStyle.Medium }).catch(() => {})
}

export async function hapticHeavy() {
  await Haptics.impact({ style: ImpactStyle.Heavy }).catch(() => {})
}
