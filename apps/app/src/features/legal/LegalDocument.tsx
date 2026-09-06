// renders the legal document component
import { BackButton } from '@/components/ui/back-button'
import { useAuthStore } from '@/store/auth'

interface Props {
  html: string
  backTo?: string
}

// renders a legal document served as its own markup, with the typography the
// rest of the application uses so the text does not arrive as a foreign page
export function LegalDocument({ html, backTo }: Props) {
  const authenticated = useAuthStore((s) => s.isAuthenticated)
  // the fallback only fires when there is no history to return to, and the profile
  // demands a session, so a visitor without one lands on the entrance instead
  const fallback = authenticated ? backTo : '/login'

  return (
    <div className="bg-white px-6 pt-6 pb-28">
      {fallback ? <BackButton to={fallback} className="mb-8" /> : null}
      <article
        className="legal-document text-sm leading-relaxed text-gray-600"
        // the markup is a static asset of the build, never anything a viewer supplies
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  )
}
