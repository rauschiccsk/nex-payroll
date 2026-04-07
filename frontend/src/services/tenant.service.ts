import api from './api'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import type { TenantCreate, TenantRead, TenantUpdate } from '@/types/tenant'

const BASE = '/api/v1/tenants'

export async function listTenants(
  params?: PaginationParams,
): Promise<PaginatedResponse<TenantRead>> {
  const response = await api.get<PaginatedResponse<TenantRead>>(BASE, { params })
  return response.data
}

export async function getTenant(id: string): Promise<TenantRead> {
  const response = await api.get<TenantRead>(`${BASE}/${id}`)
  return response.data
}

export async function createTenant(data: TenantCreate): Promise<TenantRead> {
  const response = await api.post<TenantRead>(BASE, data)
  return response.data
}

export async function updateTenant(id: string, data: TenantUpdate): Promise<TenantRead> {
  const response = await api.patch<TenantRead>(`${BASE}/${id}`, data)
  return response.data
}

export async function deleteTenant(id: string): Promise<void> {
  await api.delete(`${BASE}/${id}`)
}
