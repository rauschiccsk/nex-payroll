import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { EmployeeCreate, EmployeeRead, EmployeeUpdate } from '@/types/employee'

const BASE = '/api/v1/employees'

export async function listEmployees(
  params?: PaginationParams,
): Promise<PaginatedResponse<EmployeeRead>> {
  const response = await api.get<PaginatedResponse<EmployeeRead>>(BASE, { params })
  return response.data
}

export async function getEmployee(id: string): Promise<EmployeeRead> {
  const response = await api.get<EmployeeRead>(`${BASE}/${id}`)
  return response.data
}

export async function createEmployee(data: EmployeeCreate): Promise<EmployeeRead> {
  const response = await api.post<EmployeeRead>(BASE, data)
  return response.data
}

export async function updateEmployee(id: string, data: EmployeeUpdate): Promise<EmployeeRead> {
  const response = await api.patch<EmployeeRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteEmployee(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
