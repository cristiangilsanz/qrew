// implements privacy
import { createFileRoute } from '@tanstack/react-router'

import { LegalDocument } from '@/features/legal/LegalDocument'
import html from '@/features/legal/privacy.html?raw'

export const Route = createFileRoute('/privacy')({
  component: PrivacyPage,
})

// renders the privacy page component
function PrivacyPage() {
  return <LegalDocument html={html} backTo="/profile/about" />
}
