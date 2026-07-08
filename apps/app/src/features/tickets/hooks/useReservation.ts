import { useQuery } from '@tanstack/react-query'

import { type ReservationStatus, ticketsApi } from '../api'

const TERMINAL_STATUSES: ReservationStatus[] = ['paid', 'cancelled', 'expired']

export function useReservation(reservationId: string, pollUntilPaid = false) {
  return useQuery({
    queryKey: ['reservation', reservationId],
    queryFn: () => ticketsApi.getReservation(reservationId),
    enabled: !!reservationId,
    refetchInterval: (query) => {
      if (!pollUntilPaid) return false
      const status = query.state.data?.status
      if (status && TERMINAL_STATUSES.includes(status)) return false
      return 2_000
    },
  })
}
