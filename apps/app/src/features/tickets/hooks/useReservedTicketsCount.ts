import { useTickets } from './useTickets'

export function useReservedTicketsCount(): number {
  const { data: tickets } = useTickets()
  return tickets?.filter((t) => t.state === 'reserved').length ?? 0
}
