import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { CheckCircle2, ScanLine, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { useOrgEvents } from '@/features/organiser/hooks/useOrgEvents'
import { useScanner } from '@/features/scanner/hooks/useScanner'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/management/$orgId/events/$eventId/scan')({
  component: ScanPage,
})

function ScanPage() {
  const { t } = useTranslation()
  const { orgId, eventId } = Route.useParams()
  const navigate = useNavigate()

  const { data: eventsData } = useOrgEvents(orgId)
  const event = eventsData?.items.find((e) => e.id === eventId)

  const { videoRef, phase, scanResult, scanCount, errorMsg, startScanning } = useScanner({
    eventId,
    eventName: event?.name ?? 'Event',
    notSupportedMessage: t('organiser.scanner.notSupported'),
  })

  return (
    <div className="flex h-screen flex-col bg-black">
      <div className="safe-top flex items-center gap-3 p-4">
        <BackButton
          to="/management/$orgId/events/$eventId/"
          params={{ orgId, eventId }}
          className="text-white"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white">{event?.name ?? '—'}</p>
          <p className="text-xs text-white/50">{t('organiser.scanner.title')}</p>
        </div>
        {scanCount > 0 && (
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/70">
            {scanCount} {t('organiser.scanner.scanned')}
          </span>
        )}
      </div>

      {/* Camera viewfinder */}
      <div className="relative flex-1 overflow-hidden">
        <video ref={videoRef} className="h-full w-full object-cover" playsInline muted autoPlay />

        {/* Overlay when not scanning */}
        {phase !== 'scanning' && phase !== 'result' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 bg-black/70 px-8">
            {phase === 'init' && (
              <>
                <p className="text-center text-sm text-white/70">{t('organiser.scanner.prompt')}</p>
                <button
                  onClick={() => void startScanning()}
                  className="bg-primary flex items-center gap-2 rounded-full px-8 py-3 text-sm font-semibold text-white"
                >
                  <ScanLine className="h-4 w-4 shrink-0" />
                  {t('organiser.scanner.start')}
                </button>
              </>
            )}
            {phase === 'error' && (
              <>
                <XCircle className="h-12 w-12 text-red-400" />
                <p className="text-center text-sm whitespace-pre-line text-white/70">{errorMsg}</p>
                <button
                  onClick={() =>
                    void navigate({
                      to: '/management/$orgId/events/$eventId/',
                      params: { orgId, eventId },
                    })
                  }
                  className="rounded-full bg-white/10 px-8 py-3 text-sm font-semibold text-white"
                >
                  {t('common.back')}
                </button>
              </>
            )}
          </div>
        )}

        {/* Scanning viewfinder corners */}
        {phase === 'scanning' && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative h-64 w-64">
              <span className="absolute top-0 left-0 h-8 w-8 rounded-tl-lg border-t-2 border-l-2 border-white" />
              <span className="absolute top-0 right-0 h-8 w-8 rounded-tr-lg border-t-2 border-r-2 border-white" />
              <span className="absolute bottom-0 left-0 h-8 w-8 rounded-bl-lg border-b-2 border-l-2 border-white" />
              <span className="absolute right-0 bottom-0 h-8 w-8 rounded-br-lg border-r-2 border-b-2 border-white" />
            </div>
          </div>
        )}

        {/* Scan result flash */}
        {phase === 'result' && scanResult && (
          <div
            className={cn(
              'absolute inset-0 flex flex-col items-center justify-center gap-4',
              scanResult.allowed ? 'bg-green-500/80' : 'bg-red-500/80',
            )}
          >
            {scanResult.allowed ? (
              <CheckCircle2 className="h-24 w-24 text-white" />
            ) : (
              <XCircle className="h-24 w-24 text-white" />
            )}
            <p className="text-xl font-bold text-white">
              {scanResult.allowed
                ? t('organiser.scanner.admitted')
                : t('organiser.scanner.rejected')}
            </p>
            {scanResult.reason && (
              <p className="text-sm text-white/80">{scanResult.reason.replace(/_/g, ' ')}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
