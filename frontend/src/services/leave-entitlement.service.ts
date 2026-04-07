import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type {
  LeaveEntitlementCreate,
  LeaveEntitlementRead,
  LeaveEntitlementUpdate,
} from '@/types/leave-entitlement'

const BASE = '/api/v1/leave-entitlements'

export async function listLeaveEntitlements(
  params?: PaginationParams & { employee_id?: string; year?: number },
): Promise<PaginatedResponse<LeaveEntitlementRead>> {
  const response = await api.get<PaginatedResponse<LeaveEntitlementRead>>(BASE, { params })
  return response.data
}

export async function getLeaveEntitlement(id: string): Promise<LeaveEntitlementRead> {
  const response = await api.get<LeaveEntitlementRead>(`${BASE}/${id}`)
  return response.data
}

export async function createLeaveEntitlement(
  data: LeaveEntitlementCreate,
): Promise<LeaveEntitlementRead> {
  const response = await api.post<LeaveEntitlementRead>(BASE, data)
  return response.data
}

export async function updateLeaveEntitlement(
  id: string,
  data: LeaveEntitlementUpdate,
): Promise<LeaveEntitlementRead> {
  const response = await api.patch<LeaveEntitlementRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteLeaveEntitlement(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
