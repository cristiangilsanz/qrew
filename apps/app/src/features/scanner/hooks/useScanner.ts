// provides use scanner
import type { PluginListenerHandle } from '@capacitor/core'
import { Capacitor } from '@capacitor/core'
import { BarcodeFormat, BarcodeScanner } from '@capacitor-mlkit/barcode-scanning'
import { useCallback, useEffect, useRef, useState } from 'react'

import { scannerApi } from '@/features/scanner/api'
import { hapticHeavy, hapticLight } from '@/lib/haptics'

export type ScanResult = {
  allowed: boolean
  reason: string | null
  ticketId: string | null
} | null

export type ScanPhase = 'init' | 'scanning' | 'result' | 'error'

interface BarcodeDetector {
  detect(image: ImageBitmapSource): Promise<Array<{ rawValue: string }>>
}
// eslint-disable-next-line no-redeclare
declare const BarcodeDetector: {
  new (options: { formats: string[] }): BarcodeDetector
  getSupportedFormats(): Promise<string[]>
}

interface UseScannerOptions {
  eventId: string
  eventName: string
  notSupportedMessage: string
}

// provides use scanner
export function useScanner({ eventId, eventName, notSupportedMessage }: UseScannerOptions) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const detectorRef = useRef<BarcodeDetector | null>(null)
  const scannerTokenRef = useRef<string | null>(null)
  const rafRef = useRef<number | null>(null)
  const processingRef = useRef(false)
  const listenerRef = useRef<PluginListenerHandle | null>(null)

  const [phase, setPhase] = useState<ScanPhase>('init')
  const [scanResult, setScanResult] = useState<ScanResult>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [scanCount, setScanCount] = useState(0)

  // implements stop camera
  const stopCamera = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    if (Capacitor.isNativePlatform()) {
      void listenerRef.current?.remove()
      listenerRef.current = null
      void BarcodeScanner.stopScan().catch(() => undefined)
      document.body.classList.remove('scanner-active')
    }
  }, [])

  useEffect(() => () => stopCamera(), [stopCamera])

  // implements start detect loop
  function startDetectLoop() {
    if (!detectorRef.current || !videoRef.current) return
    const detector = detectorRef.current
    const video = videoRef.current

    // implements tick
    async function tick() {
      if (processingRef.current) return
      if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
        try {
          const barcodes = await detector.detect(video)
          if (barcodes.length > 0) {
            void handleScan(barcodes[0].rawValue)
            return
          }
        } catch {
          // ignore detection errors
        }
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
  }

  // handles handle scan
  const handleScan = useCallback(
    async (raw: string) => {
      if (processingRef.current || !scannerTokenRef.current) return
      processingRef.current = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      try {
        const result = await scannerApi.validateEntry(scannerTokenRef.current, raw)
        setScanResult({
          allowed: result.allowed,
          reason: result.reason,
          ticketId: result.ticket_id,
        })
        setScanCount((c) => c + 1)
        void (result.allowed ? hapticLight() : hapticHeavy())
        setPhase('result')
        setTimeout(() => {
          setPhase('scanning')
          setScanResult(null)
          processingRef.current = false
          startDetectLoop()
        }, 2000)
      } catch {
        setScanResult({ allowed: false, reason: 'error', ticketId: null })
        setPhase('result')
        setTimeout(() => {
          setPhase('scanning')
          setScanResult(null)
          processingRef.current = false
          startDetectLoop()
        }, 2000)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  // scans with the native detector when the web api is unavailable
  async function startNativeScanning() {
    const permission = await BarcodeScanner.requestPermissions()
    if (permission.camera !== 'granted' && permission.camera !== 'limited') {
      setErrorMsg(notSupportedMessage)
      setPhase('error')
      return
    }

    const available = await BarcodeScanner.isGoogleBarcodeScannerModuleAvailable()
    if (!available.available) {
      await BarcodeScanner.installGoogleBarcodeScannerModule()
    }

    document.body.classList.add('scanner-active')
    listenerRef.current = await BarcodeScanner.addListener('barcodesScanned', (event) => {
      const raw = event.barcodes[0]?.rawValue
      if (raw) void handleScan(raw)
    })
    await BarcodeScanner.startScan({ formats: [BarcodeFormat.QrCode] })
    setPhase('scanning')
  }

  // implements start scanning
  async function startScanning() {
    try {
      const tok = await scannerApi.createForEvent(eventId, `${eventName} scanner`)
      scannerTokenRef.current = tok.token

      if (Capacitor.isNativePlatform()) {
        await startNativeScanning()
        return
      }

      if (typeof BarcodeDetector === 'undefined') {
        setErrorMsg(notSupportedMessage)
        setPhase('error')
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      detectorRef.current = new BarcodeDetector({ formats: ['qr_code'] })
      setPhase('scanning')
      startDetectLoop()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMsg(msg)
      setPhase('error')
    }
  }

  return {
    videoRef,
    phase,
    scanResult,
    scanCount,
    errorMsg,
    startScanning,
  }
}
