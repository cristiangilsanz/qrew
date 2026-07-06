import { apiClient } from '@/lib/api'

export interface Passkey {
  id: string
  name: string | null
  aaguid: string
  last_used_at: string | null
  created_at: string
}

export const passkeysApi = {
  list: () =>
    apiClient
      .get<{ items: Passkey[]; next_cursor: string | null }>('/v1/auth/passkeys/')
      .then((r) => r.data),

  remove: (id: string) => apiClient.delete(`/v1/auth/passkeys/${id}`),

  rename: (id: string, name: string) =>
    apiClient.patch<Passkey>(`/v1/auth/passkeys/${id}`, { name }).then((r) => r.data),
}
