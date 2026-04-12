import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  PayrollCreate,
  PayrollRead,
  PayrollUpdate,
  PayrollStatus,
} from '@/types/payroll'

const BASE = '/api/v1/payrolls'

export interface PayrollListParams extends PaginationParams {
  tenant_id?: string
  employee_id?: string
  period_year?: number
  period_month?: number
  status?: PayrollStatus
}

export async function listPayrolls(
  params?: PayrollListParams,
): Promise<PaginatedResponse<PayrollRead>> {
  const response = await api.get<PaginatedResponse<PayrollRead>>(BASE, { params })
  return response.data
}

export async function getPayroll(id: string): Promise<PayrollRead> {
  const response = await api.get<PayrollRead>(`${BASE}/${id}`)
  return response.data
}

export async function createPayroll(data: PayrollCreate): Promise<PayrollRead> {
  const response = await api.post<PayrollRead>(BASE, data)
  return response.data
}

export async function updatePayroll(id: string, data: PayrollUpdate): Promise<PayrollRead> {
  const response = await api.patch<PayrollRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deletePayroll(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}

/** Transition payroll to calculated status */
export async function calculatePayroll(id: string): Promise<PayrollRead> {
  const response = await api.post<PayrollRead>(`${BASE}/${id}/calculate`)
  return response.data
}

/** Approve a calculated payroll */
export async function approvePayroll(id: string): Promise<PayrollRead> {
  const response = await api.post<PayrollRead>(`${BASE}/${id}/approve`)
  return response.data
}
