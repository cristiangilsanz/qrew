// provides use devices
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { authApi } from '@/features/auth/api'
import { useAuthStore } from '@/store/auth'

import { profileApi } from '../api'

// provides use devices
export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: profileApi.getDevices,
  })
}

// provides use revoke device
export function useRevokeDevice() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  // implements clear session
  const clearSession = useAuthStore((s) => s.clearSession)
  // implements refresh token
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const navigate = useNavigate()
  return useMutation({
    // implements mutation fn
    mutationFn: ({ deviceId }: { deviceId: string; isCurrent: boolean }) =>
      profileApi.revokeDevice(deviceId),
    // handles on success
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

// provides use revoke all devices
export function useRevokeAllDevices() {
  const { t } = useTranslation()
  // implements clear session
  const clearSession = useAuthStore((s) => s.clearSession)
  // implements refresh token
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: profileApi.revokeAllDevices,
    // handles on success
    onSuccess: () => {
      toast.success(t('profile.security.devicesRevokedAll'))
      if (refreshToken) void authApi.logout(refreshToken).catch(() => {})
      clearSession()
      void navigate({ to: '/login' })
    },
  })
}
