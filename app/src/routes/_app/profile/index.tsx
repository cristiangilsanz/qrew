import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/profile/')({
  component: ProfilePage,
})

function ProfilePage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold">Profile</h1>
    </div>
  )
}
