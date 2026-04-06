import { createStore } from 'zustand/vanilla'

// ── Auth State ─────────────────────────────────────────────
export interface AuthState {
  token: string | null
  tenantId: string | null
  setToken: (token: string | null) => void
  setTenantId: (tenantId: string | null) => void
  clear: () => void
}

// Vanilla store (framework-agnostic) so axios interceptors can access it
// without React hooks.
export const authStore = createStore<AuthState>((set) => ({
  token: null,
  tenantId: null,
  setToken: (token) => set({ token }),
  setTenantId: (tenantId) => set({ tenantId }),
  clear: () => set({ token: null, tenantId: null }),
}))
