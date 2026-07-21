import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { profileApi } from '../api'

export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: profileApi.getDevices,
  })
}

export function useRevokeDevice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (deviceId: string) => profileApi.revokeDevice(deviceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['devices'] }),
  })
}

export function useRevokeAllDevices() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profileApi.revokeAllDevices,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['devices'] }),
  })
}
