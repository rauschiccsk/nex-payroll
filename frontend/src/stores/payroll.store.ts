import { createStore } from 'zustand/vanilla'

export interface PayrollStoreState {
  currentPeriod: { year: number; month: number } | null
  filters: Record<string, string>
  setCurrentPeriod: (period: PayrollStoreState['currentPeriod']) => void
  setFilters: (filters: Record<string, string>) => void
}

export const payrollStore = createStore<PayrollStoreState>((set) => ({
  currentPeriod: null,
  filters: {},
  setCurrentPeriod: (currentPeriod) => set({ currentPeriod }),
  setFilters: (filters) => set({ filters }),
}))
