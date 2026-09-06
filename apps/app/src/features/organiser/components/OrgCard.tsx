// renders the org card component
import { Link } from '@tanstack/react-router'
import { Building2, ChevronRight } from 'lucide-react'

interface OrgCardItem {
  id: string
  slug: string
  name: string
}

interface Props {
  org: OrgCardItem
}

// renders the org card component
export function OrgCard({ org }: Props) {
  return (
    <Link
      to="/management/$orgId"
      params={{ orgId: org.id }}
      className="flex w-full items-center gap-3 px-4 py-4 transition-colors hover:bg-white/[0.04]"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
        <Building2 className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{org.name}</p>
        <p className="text-muted-foreground truncate text-xs">@{org.slug}</p>
      </div>
      <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
    </Link>
  )
}
