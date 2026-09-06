// provides use reservation payment
import { useQuery } from '@tanstack/react-query'

import { type PaymentStatus, ticketsApi } from '../api'

const TERMINAL_STATUSES: PaymentStatus[] = ['succeeded', 'failed', 'refunded']

// polls the payment of a reservation, which also reconciles it against the provider
export function useReservationPayment(reservationId: string, enabled = false) {
  return useQuery({
    queryKey: ['reservation-payment', reservationId],
    // implements query fn
    queryFn: () => ticketsApi.getReservationPayment(reservationId),
    enabled: enabled && !!reservationId,
    retry: false,
    // implements refetch interval
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status && TERMINAL_STATUSES.includes(status)) return false
      return 3_000
    },
  })
}
