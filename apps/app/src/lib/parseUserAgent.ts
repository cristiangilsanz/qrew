export type DeviceType = 'mobile' | 'tablet' | 'desktop'

export interface ParsedUA {
  browser: string
  os: string
  deviceType: DeviceType
  label: string
}

export function parseUserAgent(ua: string | null): ParsedUA {
  if (!ua) return { browser: 'Unknown browser', os: 'Unknown OS', deviceType: 'desktop', label: 'Unknown device' }

  const browser = detectBrowser(ua)
  const os = detectOS(ua)
  const deviceType = detectDeviceType(ua)

  return { browser, os, deviceType, label: `${browser} on ${os}` }
}

function detectBrowser(ua: string): string {
  if (/Edg\//.test(ua)) return 'Edge'
  if (/OPR\/|Opera\//.test(ua)) return 'Opera'
  if (/SamsungBrowser\//.test(ua)) return 'Samsung Browser'
  if (/Firefox\//.test(ua)) return 'Firefox'
  if (/Chrome\//.test(ua)) return 'Chrome'
  if (/Safari\//.test(ua) && !/Chrome/.test(ua)) return 'Safari'
  return 'Browser'
}

function detectOS(ua: string): string {
  if (/iPhone/.test(ua)) return 'iPhone'
  if (/iPad/.test(ua)) return 'iPad'
  if (/Android/.test(ua)) return 'Android'
  if (/Windows NT/.test(ua)) return 'Windows'
  if (/Mac OS X/.test(ua)) return 'macOS'
  if (/Linux/.test(ua)) return 'Linux'
  return 'Unknown OS'
}

function detectDeviceType(ua: string): DeviceType {
  if (/iPad/.test(ua)) return 'tablet'
  if (/iPhone|Android.*Mobile|Mobile/.test(ua)) return 'mobile'
  return 'desktop'
}
