import { Link } from '@tanstack/react-router'

import { Card, CardContent } from '@/components/ui/card'

import type { Organisation } from '../api'

interface Props {
  org: Organisation
}

export function OrgCard({ org }: Props) {
  return (
    <Link to="/organiser/$orgId" params={{ orgId: org.id }}>
      <Card className="hover:bg-muted/50 cursor-pointer transition-colors">
        <CardContent className="p-4">
          <p className="font-medium">{org.name}</p>
          <p className="text-muted-foreground text-sm">@{org.slug}</p>
        </CardContent>
      </Card>
    </Link>
  )
}
