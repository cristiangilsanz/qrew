// provides use reservation
import { useQuery } from '@tanstack/react-query'

import { type ReservationStatus, ticketsApi } from '../api'

const TERMINAL_STATUSES: ReservationStatus[] = ['paid', 'cancelled', 'expired']

// provides use reservation
export function useReservation(reservationId: string, pollUntilPaid = false) {
  return useQuery({
    queryKey: ['reservation', reservationId],
    // implements query fn
    queryFn: () => ticketsApi.getReservation(reservationId),
    enabled: !!reservationId,
    // implements refetch interval
    refetchInterval: (query) => {
      if (!pollUntilPaid) return false
      const status = query.state.data?.status
      if (status && TERMINAL_STATUSES.includes(status)) return false
      return 2_000
    },
  })
}
