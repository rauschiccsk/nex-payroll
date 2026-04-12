import { createStore } from 'zustand/vanilla'

export interface ReferenceState {
  healthInsurers: Array<{ id: string; name: string; code: string }>
  rates: Array<{ id: string; name: string; rate: string }>
  brackets: Array<{ id: string; threshold: string; rate: string }>
  setHealthInsurers: (items: ReferenceState['healthInsurers']) => void
  setRates: (items: ReferenceState['rates']) => void
  setBrackets: (items: ReferenceState['brackets']) => void
}

export const referenceStore = createStore<ReferenceState>((set) => ({
  healthInsurers: [],
  rates: [],
  brackets: [],
  setHealthInsurers: (healthInsurers) => set({ healthInsurers }),
  setRates: (rates) => set({ rates }),
  setBrackets: (brackets) => set({ brackets }),
}))
