import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { authApi } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: profileApi.getDevices,
  })
}

export function useRevokeDevice() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const clearSession = useAuthStore((s) => s.clearSession)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: ({ deviceId }: { deviceId: string; isCurrent: boolean }) =>
      profileApi.revokeDevice(deviceId),
    onSuccess: (_data, { isCurrent }) => {
      toast.success(t('profile.security.deviceRevoked'))
      if (isCurrent) {
        if (refreshToken) void authApi.logout(refreshToken).catch(() => {})
        clearSession()
        void navigate({ to: '/login' })
      } else {
        void queryClient.invalidateQueries({ queryKey: ['devices'] })
      }
    },
  })
}

export function useRevokeAllDevices() {
  const { t } = useTranslation()
  const clearSession = useAuthStore((s) => s.clearSession)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: profileApi.revokeAllDevices,
    onSuccess: () => {
      toast.success(t('profile.security.devicesRevokedAll'))
      if (refreshToken) void authApi.logout(refreshToken).catch(() => {})
      clearSession()
      void navigate({ to: '/login' })
    },
  })
}
