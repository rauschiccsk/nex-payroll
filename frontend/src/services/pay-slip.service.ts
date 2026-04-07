import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { PaySlipCreate, PaySlipRead, PaySlipUpdate } from '@/types/pay-slip'

const BASE = '/api/v1/payslips'

export async function listPaySlips(
  params?: PaginationParams & {
    tenant_id?: string
    employee_id?: string
    payroll_id?: string
    period_year?: number
    period_month?: number
  },
): Promise<PaginatedResponse<PaySlipRead>> {
  const response = await api.get<PaginatedResponse<PaySlipRead>>(BASE, { params })
  return response.data
}

export async function getPaySlip(id: string): Promise<PaySlipRead> {
  const response = await api.get<PaySlipRead>(`${BASE}/${id}`)
  return response.data
}

export async function createPaySlip(data: PaySlipCreate): Promise<PaySlipRead> {
  const response = await api.post<PaySlipRead>(BASE, data)
  return response.data
}

export async function updatePaySlip(id: string, data: PaySlipUpdate): Promise<PaySlipRead> {
  const response = await api.patch<PaySlipRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deletePaySlip(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
