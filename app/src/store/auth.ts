import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

interface AuthState {
  accessToken: string | null
  isAuthenticated: boolean
  setAccessToken: (token: string) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    immer((set) => ({
      accessToken: null,
      isAuthenticated: false,
      setAccessToken: (token) =>
        set((state) => {
          state.accessToken = token
          state.isAuthenticated = true
        }),
      clearSession: () =>
        set((state) => {
          state.accessToken = null
          state.isAuthenticated = false
        }),
    })),
    {
      name: 'qrew-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ accessToken: state.accessToken }),
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) state.isAuthenticated = true
      },
    },
  ),
)
