// implements auth
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
      // implements set access token
      setAccessToken: (token) =>
        set((state) => {
          state.accessToken = token
          state.isAuthenticated = true
        }),
      // implements set tokens
      setTokens: (accessToken, refreshToken) =>
        set((state) => {
          state.accessToken = accessToken
          state.refreshToken = refreshToken
          state.isAuthenticated = true
        }),
      // implements set setup token
      setSetupToken: (token) =>
        set((state) => {
          state.setupToken = token
          state.isSetupPending = true
        }),
      // implements set totp token
      setTotpToken: (token) =>
        set((state) => {
          state.totpToken = token
          state.isTotpPending = true
        }),
      // implements clear totp pending
      clearTotpPending: () =>
        set((state) => {
          state.totpToken = null
          state.isTotpPending = false
        }),
      // implements set phone number
      setPhoneNumber: (phone) =>
        set((state) => {
          state.phoneNumber = phone
        }),
      // implements complete setup
      completeSetup: (token) =>
        set((state) => {
          state.accessToken = token
          state.isAuthenticated = true
          state.setupToken = null
          state.isSetupPending = false
        }),
      // implements clear session
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
      // implements partialize
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        setupToken: state.setupToken,
        totpToken: state.totpToken,
        phoneNumber: state.phoneNumber,
        isSetupPending: state.isSetupPending,
        isTotpPending: state.isTotpPending,
      }),
      // handles on rehydrate storage
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) state.isAuthenticated = true
      },
    },
  ),
)
