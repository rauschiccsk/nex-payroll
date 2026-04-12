import { createStore } from 'zustand/vanilla'

// ── Current User ──────────────────────────────────────────
export interface CurrentUser {
  id: string
  email: string
  username: string
  role: 'director' | 'accountant' | 'employee'
  tenant_id: string
  is_active: boolean
}

// ── Auth State ─────────────────────────────────────────────
export interface AuthState {
  token: string | null
  tenantId: string | null
  currentUser: CurrentUser | null
  setToken: (token: string | null) => void
  setTenantId: (tenantId: string | null) => void
  setCurrentUser: (user: CurrentUser | null) => void
  clear: () => void
}

// Vanilla store (framework-agnostic) so axios interceptors can access it
// without React hooks.
export const authStore = createStore<AuthState>((set) => ({
  token: null,
  tenantId: null,
  currentUser: null,
  setToken: (token) => set({ token }),
  setTenantId: (tenantId) => set({ tenantId }),
  setCurrentUser: (currentUser) => set({ currentUser }),
  clear: () => set({ token: null, tenantId: null, currentUser: null }),
}))
