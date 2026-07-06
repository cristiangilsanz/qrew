import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

interface AuthState {
  accessToken: string | null
  setupToken: string | null
  phoneNumber: string | null
  isAuthenticated: boolean
  isSetupPending: boolean
  setAccessToken: (token: string) => void
  setSetupToken: (token: string) => void
  setPhoneNumber: (phone: string) => void
  completeSetup: (token: string) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    immer((set) => ({
      accessToken: null,
      setupToken: null,
      phoneNumber: null,
      isAuthenticated: false,
      isSetupPending: false,
      setAccessToken: (token) =>
        set((state) => {
          state.accessToken = token
          state.isAuthenticated = true
        }),
      setSetupToken: (token) =>
        set((state) => {
          state.setupToken = token
          state.isSetupPending = true
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
          state.setupToken = null
          state.phoneNumber = null
          state.isAuthenticated = false
          state.isSetupPending = false
        }),
    })),
    {
      name: 'qrew-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        setupToken: state.setupToken,
        phoneNumber: state.phoneNumber,
        isSetupPending: state.isSetupPending,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) state.isAuthenticated = true
      },
    },
  ),
)
