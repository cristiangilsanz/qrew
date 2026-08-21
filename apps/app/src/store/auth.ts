import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

import { preferencesStorage } from '@/lib/storage'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  setupToken: string | null
  totpToken: string | null
  phoneNumber: string | null
  isAuthenticated: boolean
  isSetupPending: boolean
  isTotpPending: boolean
  setAccessToken: (token: string) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  setSetupToken: (token: string) => void
  setTotpToken: (token: string) => void
  clearTotpPending: () => void
  setPhoneNumber: (phone: string) => void
  completeSetup: (token: string) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    immer((set) => ({
      accessToken: null,
      refreshToken: null,
      setupToken: null,
      totpToken: null,
      phoneNumber: null,
      isAuthenticated: false,
      isSetupPending: false,
      isTotpPending: false,
      setAccessToken: (token) =>
        set((state) => {
          state.accessToken = token
          state.isAuthenticated = true
        }),
      setTokens: (accessToken, refreshToken) =>
        set((state) => {
          state.accessToken = accessToken
          state.refreshToken = refreshToken
          state.isAuthenticated = true
        }),
      setSetupToken: (token) =>
        set((state) => {
          state.setupToken = token
          state.isSetupPending = true
        }),
      setTotpToken: (token) =>
        set((state) => {
          state.totpToken = token
          state.isTotpPending = true
        }),
      clearTotpPending: () =>
        set((state) => {
          state.totpToken = null
          state.isTotpPending = false
        }),
      setPhoneNumber: (phone) =>
        set((state) => {
          state.phoneNumber = phone
        }),
      completeSetup: (token) =>
        set((state) => {
          state.accessToken = token
          state.isAuthenticated = true
          state.setupToken = null
          state.isSetupPending = false
        }),
      clearSession: () =>
        set((state) => {
          state.accessToken = null
          state.refreshToken = null
          state.setupToken = null
          state.totpToken = null
          state.phoneNumber = null
          state.isAuthenticated = false
          state.isSetupPending = false
          state.isTotpPending = false
        }),
    })),
    {
      name: 'qrew-auth',
      storage: createJSONStorage(() => preferencesStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        setupToken: state.setupToken,
        totpToken: state.totpToken,
        phoneNumber: state.phoneNumber,
        isSetupPending: state.isSetupPending,
        isTotpPending: state.isTotpPending,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) state.isAuthenticated = true
      },
    },
  ),
)
