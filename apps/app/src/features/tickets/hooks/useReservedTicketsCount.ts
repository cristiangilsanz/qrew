// provides use reserved tickets count
import { useTickets } from './useTickets'

// provides use reserved tickets count
export function useReservedTicketsCount(): number {
  const { data: tickets } = useTickets()
  return tickets?.filter((t) => t.state === 'reserved').length ?? 0
}
