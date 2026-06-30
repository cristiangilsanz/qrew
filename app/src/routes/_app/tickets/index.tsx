import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/tickets/')({
  component: TicketsPage,
})

function TicketsPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold">My Tickets</h1>
    </div>
  )
}
