import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/events/')({
  component: EventsPage,
})

function EventsPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold">Events</h1>
    </div>
  )
}
