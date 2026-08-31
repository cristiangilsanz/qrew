// implements new
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { BackButton } from '@/components/ui/back-button'
import { InviteCollaboratorForm } from '@/features/organiser/components/InviteCollaboratorForm'
import { useOrgCollaborators } from '@/features/organiser/hooks/useOrgCollaborators'

export const Route = createFileRoute('/_app/management/$orgId/collaborators/new')({
  component: AddMemberPage,
})

// renders the add member page component
function AddMemberPage() {
  const { t } = useTranslation()
  const { orgId } = Route.useParams()
  const navigate = useNavigate()

  const { data: members } = useOrgCollaborators(orgId)
  // implements existing member ids
  const existingCollaboratorIds = (members ?? []).map((m) => m.user_id)

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 pb-28">
      <BackButton to="/management/$orgId/collaborators" params={{ orgId }} />
      <h1 className="text-2xl font-semibold">{t('organiser.collaborators.addMember')}</h1>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
        <InviteCollaboratorForm
          orgId={orgId}
          existingCollaboratorIds={existingCollaboratorIds}
          onSuccess={() =>
            void navigate({ to: '/management/$orgId/collaborators', params: { orgId } })
          }
        />
      </div>
    </div>
  )
}
