import { createStore } from 'zustand/vanilla'

export interface TenantState {
  currentTenant: string | null
  setTenant: (tenantId: string | null) => void
}

export const tenantStore = createStore<TenantState>((set) => ({
  currentTenant: null,
  setTenant: (tenantId) => set({ currentTenant: tenantId }),
}))
