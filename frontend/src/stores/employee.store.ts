import { createStore } from 'zustand/vanilla'

export interface EmployeeState {
  selectedEmployee: string | null
  setSelectedEmployee: (employeeId: string | null) => void
}

export const employeeStore = createStore<EmployeeState>((set) => ({
  selectedEmployee: null,
  setSelectedEmployee: (employeeId) => set({ selectedEmployee: employeeId }),
}))
