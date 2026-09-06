// implements terms
import { createFileRoute } from '@tanstack/react-router'

import { LegalDocument } from '@/features/legal/LegalDocument'
import html from '@/features/legal/terms.html?raw'

export const Route = createFileRoute('/terms')({
  component: TermsPage,
})

// renders the terms page component
function TermsPage() {
  return <LegalDocument html={html} backTo="/profile/about" />
}
