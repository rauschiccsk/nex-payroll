import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { EmployeeChildCreate, EmployeeChildRead, EmployeeChildUpdate } from '@/types/employee-child'

const BASE = '/api/v1/employee-children'

export async function listEmployeeChildren(
  params?: PaginationParams & { employee_id?: string },
): Promise<PaginatedResponse<EmployeeChildRead>> {
  const response = await api.get<PaginatedResponse<EmployeeChildRead>>(BASE, { params })
  return response.data
}

export async function getEmployeeChild(id: string): Promise<EmployeeChildRead> {
  const response = await api.get<EmployeeChildRead>(`${BASE}/${id}`)
  return response.data
}

export async function createEmployeeChild(data: EmployeeChildCreate): Promise<EmployeeChildRead> {
  const response = await api.post<EmployeeChildRead>(BASE, data)
  return response.data
}

export async function updateEmployeeChild(id: string, data: EmployeeChildUpdate): Promise<EmployeeChildRead> {
  const response = await api.patch<EmployeeChildRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteEmployeeChild(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
