import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { LeaveCreate, LeaveRead, LeaveUpdate } from '@/types/leave'

const BASE = '/api/v1/leaves'

export async function listLeaves(
  params?: PaginationParams & {
    employee_id?: string
    status?: string
    leave_type?: string
  },
): Promise<PaginatedResponse<LeaveRead>> {
  const response = await api.get<PaginatedResponse<LeaveRead>>(BASE, { params })
  return response.data
}

export async function getLeave(id: string): Promise<LeaveRead> {
  const response = await api.get<LeaveRead>(`${BASE}/${id}`)
  return response.data
}

export async function createLeave(data: LeaveCreate): Promise<LeaveRead> {
  const response = await api.post<LeaveRead>(BASE, data)
  return response.data
}

export async function updateLeave(id: string, data: LeaveUpdate): Promise<LeaveRead> {
  const response = await api.patch<LeaveRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteLeave(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
